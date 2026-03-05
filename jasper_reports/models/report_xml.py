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

import base64
import hashlib
import io
import logging
import os
import re
import time
from xml.dom.minidom import getDOMImplementation

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.safe_eval import safe_eval

from ..JasperReports.jasper_report_config import Report

_logger = logging.getLogger(__name__)

src_chars = """ '"()/*-+?¿!&$[]{}@#`'^:;<>=~%,\\"""
src_chars = str.encode(src_chars, "iso-8859-1")
dst_chars = """________________________________"""
dst_chars = str.encode(dst_chars, "iso-8859-1")


class ReportXmlFile(models.Model):
    _name = "ir.actions.report.xml.file"
    _description = "Jasper Report File"

    file = fields.Binary(required=True)
    filename = fields.Char("File Name")
    report_id = fields.Many2one("ir.actions.report", "Report", ondelete="cascade")
    default = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, values):
        result = super(ReportXmlFile, self).create(values)
        # Removed the update method for the call the create_action() of
        # ir.actions.report object
        result.report_id.update()
        return result

    def write(self, values):
        result = super(ReportXmlFile, self).write(values)
        for attachment in self:
            attachment.report_id.update()
        return result


# Inherit ir.actions.report.xml and add an action to be able to store
# .jrxml and .properties files attached to the report so they can be
# used as reports in the application.


class ReportXml(models.Model):
    _inherit = "ir.actions.report"

    jasper_output = fields.Selection(
        [
            ("html", "HTML"),
            ("csv", "CSV"),
            ("xls", "XLS"),
            ("rtf", "RTF"),
            ("odt", "ODT"),
            ("ods", "ODS"),
            ("txt", "Text"),
            ("pdf", "PDF"),
        ],
        default="pdf",
    )
    jasper_file_ids = fields.One2many(
        "ir.actions.report.xml.file", "report_id", "Files"
    )
    # To get the model name from current models in database,we add a new field
    # and it will give us model name at create and update time.
    jasper_report = fields.Boolean("Is Jasper Report?")
    report_type = fields.Selection(
        selection_add=[("jasper", "Jasper")], ondelete={"jasper": "cascade"}
    )
    file = fields.Char("File")

    def retrieve_jasper_attachment(self, record):
        """Retrieve an attachment for a specific record.

        :param record: The record owning of the attachment.
        :param attachment_name: The optional name of the attachment.
        :return: A recordset of length <=1 or None
        """
        self.ensure_one()
        attachment_obj = self.env["ir.attachment"]
        attachment_name = str(self.name) + "." + self.jasper_output
        if self.attachment:
            attachment_name = safe_eval(self.attachment, {"object": record, "time": time})
        return attachment_obj.search(
            [
                ("name", "=", attachment_name),
                ("res_model", "=", self.model),
                ("res_id", "=", record.id),
            ],
            limit=1,
        )

    def postprocess_jasper_report(self, record, buffer):
        """Hook to handle post processing during the jasper report generation.
        The basic behavior consists to create a new attachment containing the
        jasper base64 encoded.

        :param record_id: The record that will own the attachment.
        :param pdf_content: The optional name content of the file to avoid
                            reading both times.
        :return: The newly generated attachment if no AccessError, else None.
        """
        self.ensure_one()
        attachment_obj = self.env["ir.attachment"]
        attachment_name = str(self.name) + "." + self.jasper_output
        if self.attachment:
            attachment_name = safe_eval(self.attachment, {"object": record, "time": time})
        attachment_vals = {
            "name": attachment_name,
            "datas": base64.b64encode(buffer.getvalue()),
            "datas_fname": attachment_name,
            "res_model": self.model,
            "res_id": record.id,
        }
        try:
            return attachment_obj.create(attachment_vals)
        except AccessError:
            _logger.warning(
                "Cannot save %s report %r as attachment",
                self.jasper_output,
                attachment_vals["name"],
            )
        return None

    @api.model
    def render_jasper(self, docids, data):
        self.ensure_one()
        self.update()
        context = self.env.context
        uid = self.env.uid
        cr = self.env.cr
        if isinstance(docids, int):
            docids = [docids]
        docids = docids or []
        data = dict(data or {})
        doc_records = self.env[self.model].browse(docids)
        report_model_name = "report.%s" % self.report_name
        data.update({"env": self.env, "model": self.model})
        if self.attachment_use:
            streams = []
            for doc_record in doc_records:
                attachment_id = self.retrieve_jasper_attachment(doc_record)
                if not attachment_id:
                    r = Report(
                        report_model_name, cr, uid, [doc_record.id], data, context
                    )
                    jasper = r.execute()
                    jasper_content_stream = io.BytesIO(jasper)
                    attachment_id = self.postprocess_jasper_report(
                        doc_record, jasper_content_stream
                    )
                if attachment_id:
                    streams.append(io.BytesIO(attachment_id.raw))
            if not streams:
                return b"", self.jasper_output
            try:
                if self.jasper_output == "pdf" and len(streams) > 1:
                    with self._merge_pdfs(streams) as merged_stream:
                        return merged_stream.getvalue(), self.jasper_output
                if len(streams) == 1:
                    return streams[0].getvalue(), self.jasper_output
                return b"".join(stream.getvalue() for stream in streams), self.jasper_output
            finally:
                for stream in streams:
                    stream.close()
        r = Report(report_model_name, cr, uid, docids, data, context)
        jasper = r.execute()
        return jasper, self.jasper_output

    @api.model
    def _get_report_from_name(self, report_name):
        res = super(ReportXml, self)._get_report_from_name(report_name)
        if res:
            return res
        domain = [("report_type", "=", "jasper"), ("report_name", "=", report_name)]
        return self.env["ir.actions.report"].search(domain, limit=1)

    @api.model_create_multi
    def create(self, values):
        if self.env.context and self.env.context.get("jasper_report"):
            for value in values:
                model_id = value.get("model_id")
                if model_id:
                    value["model"] = self.env["ir.model"].browse(model_id).model
                value["type"] = "ir.actions.report"
                value["report_type"] = "jasper"
                value["jasper_report"] = True
        return super(ReportXml, self).create(values)

    def write(self, values):
        if self.env.context and self.env.context.get("jasper_report"):
            if "model_id" in values:
                model_id = values.get("model_id")
                values["model"] = (
                    self.env["ir.model"].browse(model_id).model if model_id else False
                )

            values["type"] = "ir.actions.report"
            values["report_type"] = "jasper"
            values["jasper_report"] = True
        return super(ReportXml, self).write(values)

    def update(self):
        for report in self:
            has_default = False
            # Browse attachments and store .jrxml and .properties
            # into jasper_reports/custom_reportsdirectory. Also add
            # or update ir.values data so they're shown on model views.for
            # attachment in self.env['ir.attachment'].browse(attachmentIds)
            for attachment in report.jasper_file_ids:
                content = attachment.file
                file_name = attachment.filename
                if not file_name or not content:
                    continue
                if not file_name.endswith(".jrxml") and not file_name.endswith(
                    ".jasper"
                ):
                    raise UserError(
                        _(
                            "%s is not supported file. Please\
                     Upload .jrxml or .jasper files only."
                        )
                        % (file_name)
                    )
                path = self.save_file(file_name, content)
                if ".jrxml" in file_name and attachment.default:
                    if has_default:
                        raise UserError(
                            _(
                                "There is more than one \
                                         report marked as default"
                            )
                        )
                    has_default = True
                    report.write({"report_file": path})
                    report.create_action()
            if not has_default:
                raise UserError(
                    _(
                        "No report has been marked as default! \
                                 You need atleast one jrxml report!"
                    )
                )
            # Ensure the report is registered so it can be used immediately
            # register_jasper_report(report.report_name, report.model)
        return True

    def save_file(self, name, value):
        path = os.path.abspath(os.path.dirname(__file__))
        path += "/../custom_reports/%s" % name

        content = self._binary_to_bytes(value)
        if os.path.isfile(path):  # check contents to be sure if need to be overwriten
            hash_of_value = hashlib.sha256(content).hexdigest()
            with open(path, "rb") as f:
                text = f.read()
            hash_of_file = hashlib.sha256(text).hexdigest()
            if hash_of_value == hash_of_file:
                _logger.warning("The hashes for %s are equal, omit saving." % name)
                path = "jasper_reports/custom_reports/%s" % name
                return path

        _logger.info(
            "The hashes for %s are non-equal or the file is non-existent. saving."
            % name
        )

        with open(path, "wb+") as f:
            f.write(content)
        path = "jasper_reports/custom_reports/%s" % name
        return path

    def normalize(self, text):
        if isinstance(text, str):
            text = text.encode("utf-8")
        return text

    def unaccent(self, text):
        src_chars_list = [
            "'",
            "(",
            ")",
            ",",
            "/",
            "*",
            "-",
            "+",
            "?",
            "¿",
            "!",
            "&",
            "$",
            "[",
            "]",
            "{",
            "}",
            "@",
            "#",
            "`",
            "^",
            ":",
            ";",
            "<",
            ">",
            "=",
            "~",
            "%",
            "\\",
        ]
        num_char_dict = {
            "1": "One",
            "2": "Two",
            "3": "Three",
            "4": "Four",
            "5": "Five",
            "6": "Six",
            "7": "Seven",
            "8": "Eight",
            "9": "Nine",
            "0": "Zero",
        }
        if isinstance(text, str):
            if text and text[0] in num_char_dict:
                text = "%s%s" % (num_char_dict.get(text[0]), text[1:])
            for src in src_chars_list:
                text = text.replace(src, "_")
        return text

    @api.model
    def _binary_to_bytes(self, value):
        if not value:
            return b""
        if isinstance(value, str):
            value = value.encode()
        return base64.b64decode(value)

    @api.model
    def _sanitize_xml_tag(self, name):
        name = self.unaccent(name or "")
        name = name.replace(" ", "_")
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        name = re.sub(r"_+", "_", name).strip("_")
        if not name:
            return "field"
        if not re.match(r"[A-Za-z_]", name[0]):
            return "n_%s" % name
        return name

    @api.model
    def _get_example_value(self, field_name, field_type):
        if field_type in ("float", "monetary"):
            return "12345.67"
        if field_type == "integer":
            return "12345"
        if field_type == "date":
            return "2009-12-31"
        if field_type == "datetime":
            return "2009-12-31 12:34:56"
        if field_type == "boolean":
            return "True"
        return field_name

    @api.model
    def generate_xml(self, env, model_name, parent_node, document, depth, first_call):
        try:
            model = env[model_name]
        except KeyError:
            return

        # First of all add "id" field
        field_node = document.createElement("id")
        parent_node.appendChild(field_node)
        value_node = document.createTextNode("1")
        field_node.appendChild(value_node)

        # Then add all fields in alphabetical order
        model_fields = model._fields
        keys_list = sorted(model_fields.keys())

        language = self.env.context.get("lang")
        fields_with_labels = {}
        if language and language != "en_US":
            fields_with_labels = model.with_context(lang=language).fields_get(
                allfields=keys_list, attributes=["string"]
            )

        for field_name in keys_list:
            label = fields_with_labels.get(field_name, {}).get("string")
            if not label:
                label = model_fields[field_name].string or field_name
            field_node = document.createElement(
                self._sanitize_xml_tag("%s-%s" % (label, field_name))
            )
            parent_node.appendChild(field_node)
            field_type = model_fields[field_name].type

            if field_type in ("many2one", "one2many", "many2many"):
                if depth <= 1:
                    continue
                comodel_name = model_fields[field_name].comodel_name
                if not comodel_name:
                    continue
                self.generate_xml(
                    env, comodel_name, field_node, document, depth - 1, False
                )
                continue

            value = self._get_example_value(field_name, field_type)
            value_node = document.createTextNode(value)
            field_node.appendChild(value_node)

        if depth > 1 and model_name != "ir.attachment":
            # Create relation with attachments
            field_node = document.createElement("Attachments-Attachments")
            parent_node.appendChild(field_node)
            self.generate_xml(
                env, "ir.attachment", field_node, document, depth - 1, False
            )

        if first_call:
            # Create relation with user
            field_node = document.createElement("User-User")
            parent_node.appendChild(field_node)
            self.generate_xml(env, "res.users", field_node, document, depth - 1, False)

            # Create special entries
            field_node = document.createElement("Special-Special")
            parent_node.appendChild(field_node)

            new_node = document.createElement("copy")
            field_node.appendChild(new_node)
            value_node = document.createTextNode("1")
            new_node.appendChild(value_node)

            new_node = document.createElement("sequence")
            field_node.appendChild(new_node)
            value_node = document.createTextNode("1")
            new_node.appendChild(value_node)

            new_node = document.createElement("subsequence")
            field_node.appendChild(new_node)
            value_node = document.createTextNode("1")
            new_node.appendChild(value_node)

    @api.model
    def create_xml(self, model, depth):
        try:
            depth = int(depth)
        except (TypeError, ValueError):
            depth = 1
        depth = max(depth, 1)

        try:
            self.env[model]
        except KeyError as error:
            raise UserError(_("Model %s is not available.") % model) from error

        document = getDOMImplementation().createDocument(None, "data", None)
        top_node = document.documentElement
        record_node = document.createElement("record")
        top_node.appendChild(record_node)
        self.generate_xml(self.env, model, record_node, document, depth, True)
        return top_node.toxml()
