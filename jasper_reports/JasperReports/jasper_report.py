##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
# Copyright (C) 2019-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import glob
import os
import re
import shutil
import tempfile

from lxml import etree

try:
    import tools
    from tools.safe_eval import safe_eval
except ImportError:
    from odoo import tools
    from odoo.tools.safe_eval import safe_eval

DATA_SOURCE_EXPRESSION_REG_EXP = re.compile(r"""\$P\{(\w+)\}""")
JRXML_BAND_SECTIONS = (
    "background",
    "title",
    "pageHeader",
    "columnHeader",
    "detail",
    "columnFooter",
    "pageFooter",
    "lastPageFooter",
    "summary",
    "noData",
)
JRXML_REPORT_ELEMENT_ATTRIBUTES = {
    "x",
    "y",
    "width",
    "height",
    "positionType",
    "stretchType",
    "isPrintRepeatedValues",
    "mode",
    "forecolor",
    "backcolor",
    "isRemoveLineWhenBlank",
    "isPrintInFirstWholeBand",
    "isPrintWhenDetailOverflows",
    "printWhenGroupChanges",
    "style",
    "uuid",
    "key",
}
JRXML_EXPRESSION_TAGS = {
    "textField": "textFieldExpression",
    "image": "imageExpression",
    "subreport": "subreportExpression",
    "chart": "chartExpression",
}
JRXML_TEXT_KINDS = {"staticText", "textField"}
JRXML_TEXT_ELEMENT_ATTRIBUTES = {
    "hTextAlign": "textAlignment",
    "vTextAlign": "verticalAlignment",
    "textAlignment": "textAlignment",
    "verticalAlignment": "verticalAlignment",
    "lineSpacing": "lineSpacing",
    "rotation": "rotation",
    "markup": "markup",
}
JRXML_FONT_ATTRIBUTES = {
    "fontName": "fontName",
    "fontSize": "size",
    "size": "size",
    "bold": "isBold",
    "isBold": "isBold",
    "italic": "isItalic",
    "isItalic": "isItalic",
    "underline": "isUnderline",
    "isUnderline": "isUnderline",
    "strikeThrough": "isStrikeThrough",
    "isStrikeThrough": "isStrikeThrough",
    "pdfFontName": "pdfFontName",
    "pdfEncoding": "pdfEncoding",
    "isPdfEmbedded": "isPdfEmbedded",
}
JRXML_TEXT_FIELD_ATTRIBUTES = {
    "pattern": "pattern",
    "blankWhenNull": "isBlankWhenNull",
    "isBlankWhenNull": "isBlankWhenNull",
    "textAdjust": "textAdjust",
}


def _local_name(tag):
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _tag_with_namespace(source_tag, local_name):
    if isinstance(source_tag, str) and source_tag.startswith("{"):
        namespace = source_tag[1:].split("}", 1)[0]
        return "{%s}%s" % (namespace, local_name)
    return local_name


def _node_text(node):
    return "".join(node.itertext()).strip() if node is not None else ""


def _find_first_child(node, accepted_names):
    names = set(accepted_names)
    for child in node:
        if _local_name(child.tag) in names:
            return child
    return None


def _normalize_font_size(value):
    try:
        float_value = float(value)
    except (TypeError, ValueError):
        return value

    if float_value.is_integer():
        return str(int(float_value))
    return str(value)


class JasperReport:
    @classmethod
    def prepare_compatible_report_path(cls, report_path):
        if not cls._requires_legacy_conversion(report_path):
            return report_path, None

        source_dir = os.path.abspath(os.path.dirname(report_path))
        temp_dir = tempfile.mkdtemp(prefix="odoo_jrxml_compat_")
        for entry in os.listdir(source_dir):
            source = os.path.join(source_dir, entry)
            destination = os.path.join(temp_dir, entry)
            if os.path.isdir(source):
                shutil.copytree(source, destination, symlinks=True)
            else:
                shutil.copy2(source, destination)

        for jrxml_path in glob.glob(os.path.join(temp_dir, "*.jrxml")):
            cls._convert_to_legacy_jrxml(jrxml_path)

        return os.path.join(temp_dir, os.path.basename(report_path)), temp_dir

    @classmethod
    def _requires_legacy_conversion(cls, report_path):
        try:
            doc = etree.parse(report_path)
        except Exception:
            return False

        root = doc.getroot()
        if _local_name(root.tag) != "jasperReport":
            return False

        if doc.xpath("/*[local-name()='jasperReport']/*[local-name()='query']"):
            return True

        if doc.xpath(
            "/*[local-name()='jasperReport']/*[local-name()='field']/*[local-name()='description']"
        ):
            return True

        if doc.xpath("//*[local-name()='element' and @kind]"):
            return True

        sections = " or ".join(
            ["local-name()='%s'" % section for section in JRXML_BAND_SECTIONS]
        )
        compact_sections = "/*[local-name()='jasperReport']/*[%s][@height or @splitType]"
        return bool(doc.xpath(compact_sections % sections))

    @classmethod
    def _convert_to_legacy_jrxml(cls, report_path):
        try:
            doc = etree.parse(report_path)
        except Exception:
            return

        root = doc.getroot()
        if _local_name(root.tag) != "jasperReport":
            return

        changed = False
        changed |= cls._convert_query_tags(doc)
        changed |= cls._normalize_field_tags(doc)
        changed |= cls._normalize_band_sections(doc)
        changed |= cls._expand_compact_elements(doc)

        if changed:
            doc.write(
                report_path,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True,
            )

    @classmethod
    def _convert_query_tags(cls, doc):
        changed = False
        query_tags = doc.xpath(
            "/*[local-name()='jasperReport']/*[local-name()='query']"
        )
        for tag in query_tags:
            tag.tag = _tag_with_namespace(tag.tag, "queryString")
            changed = True
        return changed

    @classmethod
    def _normalize_field_tags(cls, doc):
        changed = False
        field_tags = doc.xpath("/*[local-name()='jasperReport']/*[local-name()='field']")
        for field in field_tags:
            children = list(field)
            properties = []
            descriptions = []
            others = []
            for child in children:
                child_name = _local_name(child.tag)
                if child_name == "description":
                    child.tag = _tag_with_namespace(child.tag, "fieldDescription")
                    child_name = "fieldDescription"
                    changed = True
                if child_name == "property":
                    properties.append(child)
                elif child_name == "fieldDescription":
                    descriptions.append(child)
                else:
                    others.append(child)
            normalized = properties + others + descriptions
            if normalized != children:
                field[:] = normalized
                changed = True
        return changed

    @classmethod
    def _normalize_band_sections(cls, doc):
        changed = False
        sections = " or ".join(
            ["local-name()='%s'" % section for section in JRXML_BAND_SECTIONS]
        )
        section_tags = doc.xpath("/*[local-name()='jasperReport']/*[%s]" % sections)
        for section in section_tags:
            children = list(section)
            has_band_children = all(
                _local_name(child.tag) == "band" for child in children
            ) and bool(children)

            if not children:
                section.append(etree.Element(_tag_with_namespace(section.tag, "band")))
                changed = True
                children = list(section)
                has_band_children = True

            if not has_band_children:
                band = etree.Element(_tag_with_namespace(section.tag, "band"))
                for child in children:
                    section.remove(child)
                    band.append(child)
                section.append(band)
                children = list(section)
                changed = True

            if section.attrib:
                first_band = children[0]
                for key, value in list(section.attrib.items()):
                    if key == "splitType":
                        del section.attrib[key]
                        changed = True
                        continue
                    if key not in first_band.attrib:
                        first_band.set(key, value)
                    del section.attrib[key]
                    changed = True

            for band in children:
                if _local_name(band.tag) == "band" and "splitType" in band.attrib:
                    del band.attrib["splitType"]
                    changed = True
        return changed

    @classmethod
    def _expand_compact_elements(cls, doc):
        changed = False
        compact_elements = list(doc.xpath("//*[local-name()='element' and @kind]"))
        for compact in compact_elements:
            kind = compact.get("kind")
            if not kind:
                continue

            explicit = etree.Element(_tag_with_namespace(compact.tag, kind))
            report_element = etree.Element(
                _tag_with_namespace(compact.tag, "reportElement")
            )
            text_element = None
            font_element = None

            def ensure_text_element():
                nonlocal text_element
                if text_element is None:
                    text_element = etree.Element(
                        _tag_with_namespace(compact.tag, "textElement")
                    )
                return text_element

            def ensure_font_element():
                nonlocal font_element
                text_tag = ensure_text_element()
                if font_element is None:
                    font_element = etree.Element(_tag_with_namespace(compact.tag, "font"))
                    text_tag.append(font_element)
                return font_element

            for key, value in compact.attrib.items():
                if key == "kind":
                    continue
                if key in JRXML_REPORT_ELEMENT_ATTRIBUTES:
                    report_element.set(key, value)
                elif kind in JRXML_TEXT_KINDS and key in JRXML_TEXT_ELEMENT_ATTRIBUTES:
                    ensure_text_element().set(JRXML_TEXT_ELEMENT_ATTRIBUTES[key], value)
                elif kind in JRXML_TEXT_KINDS and key in JRXML_FONT_ATTRIBUTES:
                    normalized_value = value
                    if JRXML_FONT_ATTRIBUTES[key] == "size":
                        normalized_value = _normalize_font_size(value)
                    ensure_font_element().set(JRXML_FONT_ATTRIBUTES[key], normalized_value)
                elif kind == "textField" and key in JRXML_TEXT_FIELD_ATTRIBUTES:
                    explicit.set(JRXML_TEXT_FIELD_ATTRIBUTES[key], value)
                else:
                    explicit.set(key, value)
            explicit.append(report_element)
            if text_element is not None:
                explicit.append(text_element)

            for child in list(compact):
                compact.remove(child)
                if _local_name(child.tag) == "expression":
                    mapped = JRXML_EXPRESSION_TAGS.get(kind, "expression")
                    child.tag = _tag_with_namespace(child.tag, mapped)
                explicit.append(child)

            explicit.tail = compact.tail
            parent = compact.getparent()
            parent.insert(parent.index(compact), explicit)
            parent.remove(compact)
            changed = True
        return changed

    def __init__(self, file_name="", path_prefix=""):
        self.report_path = file_name
        self.path_prefix = path_prefix.strip()

        if self.path_prefix and self.path_prefix[-1] != "/":
            self.path_prefix += "/"

        self.language = "xpath"
        self.relations = []
        self.fields = {}
        self.field_names = []
        self.subreports = []
        self.datasets = []
        self.copies = 1
        self.copies_field = False
        self.is_header = False
        if file_name:
            self.extract_properties()

    def subreport_directory(self):
        return os.path.join(os.path.abspath(os.path.dirname(self.report_path)), "")

    def standard_directory(self):
        jasperdir = tools.config.get("jasperdir")
        if jasperdir:
            if jasperdir.endswith(os.sep):
                return jasperdir
            else:
                return os.path.join(jasperdir, "")
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "..", "report", ""
        )

    def extract_fields(self, field_tags):
        # fields and fieldNames
        fields = {}
        field_names = []
        for tag in field_tags:
            name = tag.get("name")
            type = tag.get("class")
            path = _node_text(_find_first_child(tag, ("fieldDescription", "description")))
            if not path:
                xpath_property = (
                    "./*[local-name()='property'"
                    " and @name='net.sf.jasperreports.xpath.field.expression']"
                )
                property_tags = tag.xpath(xpath_property)
                if property_tags:
                    path = property_tags[0].get("value", "").strip()
            # Make the path relative if it isn't already
            if path.startswith("/data/record/"):
                path = self.path_prefix + path[13:]

            # Remove language specific data from the path so:
            # Empresa-partner_id/Nom-name becomes partner_id/name
            # We need to consider the fact that the name in user's language
            # might not exist, hence the easiest thing to do is split and [-1]
            new_path = [x.split("-")[-1] for x in path.split("/")]

            path = "/".join(new_path)
            fields[path] = {
                "name": name,
                "type": type,
            }
            field_names.append(name)

        return fields, field_names

    def extract_properties(self):
        # The function will read all relevant information from the jrxml file

        doc = etree.parse(self.report_path)

        # Language
        # is XPath.
        lang_tags = doc.xpath(
            "/*[local-name()='jasperReport']/*[local-name()='queryString'"
            " or local-name()='query']"
        )
        if lang_tags:
            if lang_tags[0].get("language"):
                self.language = lang_tags[0].get("language").lower()

        # Relations
        ex_path = (
            "/*[local-name()='jasperReport']/*[local-name()='property'"
            ' and @name="ODOO_RELATIONS"]'
        )
        relation_tags = doc.xpath(ex_path)

        if relation_tags and "value" in relation_tags[0].keys():
            relation = relation_tags[0].get("value").strip()
            self.relations = [x.strip() for x in relation.split(",")]
            if relation.startswith("["):
                self.relations = safe_eval(relation_tags[0].get("value"), {})
            self.relations = [self.path_prefix + x for x in self.relations]

        if not self.relations and self.path_prefix:
            self.relations = [self.path_prefix[:-1]]

        # Repeat field
        path1 = (
            "/*[local-name()='jasperReport']/*[local-name()='property'"
            ' and @name="ODOO_COPIES_FIELD"]'
        )
        copies_field_tags = doc.xpath(path1)
        if copies_field_tags and "value" in copies_field_tags[0].keys():
            self.copies_field = self.path_prefix + copies_field_tags[0].get("value")

        # Repeat
        path2 = (
            "/*[local-name()='jasperReport']/*[local-name()='property'"
            ' and @name="ODOO_COPIES"]'
        )
        copies_tags = doc.xpath(path2)
        if copies_tags and "value" in copies_tags[0].keys():
            self.copies = int(copies_tags[0].get("value"))

        self.is_header = False
        path3 = (
            "/*[local-name()='jasperReport']/*[local-name()='property'"
            ' and @name="ODOO_HEADER"]'
        )
        header_tags = doc.xpath(path3)
        if header_tags and "value" in header_tags[0].keys():
            self.is_header = True

        field_tags = doc.xpath("/*[local-name()='jasperReport']/*[local-name()='field']")
        self.fields, self.field_names = self.extract_fields(field_tags)

        # Subreports
        # Here we expect the following structure in the .jrxml file:
        # <subreport>
        #  <dataSourceExpression><![CDATA[$P{REPORT_DATA_SOURCE}]]>
        # </dataSourceExpression>
        # <subreportExpression class="java.lang.String">
        # <![CDATA[$P{STANDARD_DIR} + "report_header.jasper"]]>
        # </subreportExpression>
        # </subreport>

        subreport_tags = doc.xpath("//*[local-name()='subreport']")

        for tag in subreport_tags:
            data_source_expression = _node_text(
                _find_first_child(tag, ("dataSourceExpression",))
            )

            if not data_source_expression:
                continue

            data_source_expression = data_source_expression.strip()
            m = DATA_SOURCE_EXPRESSION_REG_EXP.match(data_source_expression)

            if not m:
                continue

            data_source_expression = m.group(1)
            if data_source_expression == "REPORT_DATA_SOURCE":
                continue

            subreport_expression = _node_text(
                _find_first_child(tag, ("subreportExpression",))
            )
            if not subreport_expression:
                continue
            subreport_expression = subreport_expression.strip()
            subreport_expression = subreport_expression.replace(
                "$P{STANDARD_DIR}", '"%s"' % self.standard_directory()
            )
            subreport_expression = subreport_expression.replace(
                "$P{SUBREPORT_DIR}", '"%s"' % self.subreport_directory()
            )
            try:
                subreport_expression = safe_eval(subreport_expression, {})
            except Exception:
                continue
            if subreport_expression.endswith(".jasper"):
                subreport_expression = subreport_expression[:-6] + "jrxml"

            # Model
            model = ""
            path4 = (
                ".//*[local-name()='reportElement']/*[local-name()='property'"
                ' and @name="ODOO_MODEL"]'
            )
            model_tags = tag.xpath(path4)
            if model_tags and "value" in model_tags[0].keys():
                model = model_tags[0].get("value")

            path_prefix = ""
            pat = (
                ".//*[local-name()='reportElement']/*[local-name()='property'"
                ' and @name="ODOO_PATH_PREFIX"]'
            )
            path_prefix_tags = tag.xpath(pat)
            if path_prefix_tags and "value" in path_prefix_tags[0].keys():
                path_prefix = path_prefix_tags[0].get("value")

            self.is_header = False
            path5 = (
                ".//*[local-name()='reportElement']/*[local-name()='property'"
                ' and @name="ODOO_HEADER"]'
            )
            header_tags = tag.xpath(path5)

            if header_tags and "value" in header_tags[0].keys():
                self.is_header = True

            # Add our own path_prefix to subreport's path_prefix
            sub_prefix = []

            if self.path_prefix:
                sub_prefix.append(self.path_prefix)
            if path_prefix:
                sub_prefix.append(path_prefix)

            sub_prefix = "/".join(sub_prefix)

            subreport = JasperReport(subreport_expression, sub_prefix)

            self.subreports.append(
                {
                    "parameter": data_source_expression,
                    "filename": subreport_expression,
                    "model": model,
                    "pathPrefix": path_prefix,
                    "report": subreport,
                    "depth": 1,
                }
            )
            for subsub_info in subreport.subreports:
                subsub_info["depth"] += 1
                # Note hat 'parameter' (the one used to pass report's
                # DataSource) must be the same in all reports
                self.subreports.append(subsub_info)

        # Dataset
        # Here we expect the following structure in the .jrxml file:
        # <datasetRun>
        #  <dataSourceExpression><![CDATA[$P{REPORT_DATA_SOURCE}]]>
        # </dataSourceExpression>
        # </datasetRun>

        dataset_tags = doc.xpath("//*[local-name()='datasetRun']")

        for tag in dataset_tags:
            data_source_expression = _node_text(
                _find_first_child(tag, ("dataSourceExpression",))
            )
            if not data_source_expression:
                continue
            data_source_expression = data_source_expression.strip()
            m = DATA_SOURCE_EXPRESSION_REG_EXP.match(data_source_expression)
            if not m:
                continue
            data_source_expression = m.group(1)
            if data_source_expression == "REPORT_DATA_SOURCE":
                continue
            sub_dataset_name = tag.get("subDataset")
            if not sub_dataset_name:
                continue

            # Relations
            relations = []
            path8 = (
                "../../*[local-name()='reportElement']/*[local-name()='property'"
                ' and @name="ODOO_RELATIONS"]'
            )
            relation_tags = tag.xpath(path8)

            if relation_tags and "value" in relation_tags[0].keys():
                relation = relation_tags[0].get("value").strip()

                if relation.startswith("["):
                    relations = safe_eval(relation_tags[0].get("value"), {})
                else:
                    relations = [x.strip() for x in relation.split(",")]

                relations = [self.path_prefix + x for x in relations]

            if not relations and self.path_prefix:
                relations = [self.path_prefix[:-1]]

            # Repeat field
            copies_field = None
            path9 = (
                "../../*[local-name()='reportElement']/*[local-name()='property'"
                ' and @name="ODOO_COPIES_FIELD"]'
            )
            copies_field_tags = tag.xpath(path9)
            if copies_field_tags and "value" in copies_field_tags[0].keys():
                copies_field = self.path_prefix + copies_field_tags[0].get("value")

            # Repeat
            copies = None
            path11 = (
                "../../*[local-name()='reportElement']/*[local-name()='property'"
                ' and @name="ODOO_COPIES"]'
            )
            copies_tags = tag.xpath(path11)
            if copies_tags and "value" in copies_tags[0].keys():
                copies = int(copies_tags[0].get("value"))

            # Model
            model = ""
            path12 = (
                "../../*[local-name()='reportElement']/*[local-name()='property'"
                ' and @name="ODOO_MODEL"]'
            )
            model_tags = tag.xpath(path12)
            if model_tags and "value" in model_tags[0].keys():
                model = model_tags[0].get("value")

            path_prefix = ""
            path13 = (
                "../../*[local-name()='reportElement']/*[local-name()='property'"
                ' and @name="ODOO_PATH_PREFIX"]'
            )
            path_prefix_tags = tag.xpath(path13)

            if path_prefix_tags and "value" in path_prefix_tags[0].keys():
                path_prefix = path_prefix_tags[0].get("value")

            # We need to find the appropriate subDataset definition
            # for this dataset run.
            path14 = "//*[local-name()='subDataset' and @name='%s']"
            sub_datasets = doc.xpath(path14 % sub_dataset_name)
            if not sub_datasets:
                continue
            sub_dataset = sub_datasets[0]
            field_tags = sub_dataset.xpath("./*[local-name()='field']")
            fields, field_names = self.extract_fields(field_tags)

            dataset = JasperReport()
            dataset.fields = fields
            dataset.field_names = field_names
            dataset.relations = relations
            dataset.copies_field = copies_field
            dataset.copies = copies
            self.subreports.append(
                {
                    "parameter": data_source_expression,
                    "model": model,
                    "pathPrefix": path_prefix,
                    "report": dataset,
                    "filename": "DATASET",
                }
            )
