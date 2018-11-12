[![Build Status](https://travis-ci.org/JayVora-SerpentCS/Jasperreports_odoo.svg?branch=11.0)](https://travis-ci.org/JayVora-SerpentCS/Jasperreports_odoo)

# Jasper Report
This Module Gives The Features for creating Jasper Reports

Source : https://launchpad.net/openobject-jasper-reports

Blog for Installation : http://www.serpentcs.com/serpentcs-jasper-report-openerpodoo

![alt text](/jasper_reports/static/description/apps.png)

## Configure Java path
In your Odoo web interface, under the Company Data -> Jasper Configuration, add java path.

![alt text](/jasper_reports/static/description/java_path.png)

## Jasper Report Menu
In your Odoo web interface, under the Technical section, jasper reports menu is there.

![alt text](/jasper_reports/static/description/jasper_menu.png)


## Jasper Data Template
From your Jasper Menu, Create a jasper reports data template file.

![alt text](/jasper_reports/static/description/data_template.png)

## Design Jasper Report
In Jasper Studio, import the .xml file which was generated from Odoo and design your Jasper Report as .jrxml.

![alt text](/jasper_reports/static/description/jasper_studio.png)

## Create Jasper Report
Create a jasper reports for your module with your .jrxml file.

![alt text](/jasper_reports/static/description/create_report.png)

Demo reports can be founded in jasper_reports/demo folder.

## Print Jasper Report

![alt text](/jasper_reports/static/description/print_report.png)

## Example Of Jasper Report

![alt text](/jasper_reports/static/description/example.png)







**If you are using workers, do use the jasper_load module and mention the module among the Server Wise load modules.
i.e.: load=web,jasper_load**

Help us do better by donating to us and motivating us : http://www.serpentcs.com/page/donate-to-serpentcs
Thanks.
