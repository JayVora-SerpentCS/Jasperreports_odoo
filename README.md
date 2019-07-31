# Jasper Report

[![Build Status](https://travis-ci.org/JayVora-SerpentCS/Jasperreports_odoo.svg?branch=12.0)](https://travis-ci.org/JayVora-SerpentCS/Jasperreports_odoo)

This Module Gives The Features for creating Jasper Reports


##### [Source](https://launchpad.net/openobject-jasper-reports)

##### [Blog for Installation](http://www.serpentcs.com/serpentcs-jasper-report-openerpodoo)

##### [Documentation](https://github.com/JayVora-SerpentCS/Jasperreports_odoo/wiki/Documentation)

### Table of contents
* [Usage](#usage)
* [Known Issues](#known-issues)
* [Bug Tracker](#bug-tracker)


## Usage

![Apps](/jasper_reports/static/description/apps.png)

### Configure Java path
In your Odoo web interface, under the Company Data -> Jasper Configuration, add java path.

![Java Path](/jasper_reports/static/description/java_path.png)

### Jasper Report Menu
In your Odoo web interface, under the Technical section, jasper reports menu is there.

![Jasper Menu](/jasper_reports/static/description/jasper_menu.png)


### Jasper Data Template
From your Jasper Menu, Create a jasper reports data template file.

![Data Template](/jasper_reports/static/description/data_template.png)

### Design Jasper Report
In Jasper Studio, import the .xml file which was generated from Odoo and design your Jasper Report as .jrxml.

![Jasper Studio](/jasper_reports/static/description/jasper_studio.png)

### Create Jasper Report
Create a jasper reports for your module with your .jrxml file.

![Create Report](/jasper_reports/static/description/create_report.png)

Demo reports can be founded in jasper_reports/demo folder.

### Print Jasper Report

![Print Report](/jasper_reports/static/description/print_report.png)

### Example Of Jasper Report

![Example](/jasper_reports/static/description/example.png)

## Known Issues

If you are using workers, do use the `jasper_load` module and mention the module among the Server Wise load modules.
i.e.: `load=web,jasper_load`

## Bug Tracker

Bugs are tracked on [GitHub Issues](https://github.com/JayVora-SerpentCS/Jasperreports_odoo/issues).
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed
[feedback](https://github.com/JayVora-SerpentCS/Jasperreports_odoo/issues/new?body=version:%2012.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**%0A%0A**Screenshots**).
