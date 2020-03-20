# salesforce-attachment-download

Python script to download Salesforce Notes & Attachments.
It's using ProcessPoolExecutor to run downloads in parallell which 
makes the experience nicer if you have a large number of files.

## Getting Started

Download the script, satisfy requirements.txt and you're good to go!

## ContentNote

Since ContentNote cannot be related to a record on an insert 
(like with ContentVersion) you have to do a second insert of
ContentDocumentLinks 
(https://help.salesforce.com/articleView?id=000339316&language=en_US&type=1&mode=1).

In the content_notes.csv file the columns needed for the ContentDocumentLink
insert is added so that after a successful insert you can take the success log
and insert the ContentDocumentLinks, you can auto match all columns but the 
ContentDocumentId one which will be the Id column in the success log.

You can configure ShareType and Visibility in the ini-file if you want something
special.

## Prerequisites

simple-salesforce (https://github.com/simple-salesforce/simple-salesforce)

## Usage

1. Copy download.ini.template to download.ini and fill it out
2. Launch the script

```
usage: download.py [-h] -q query

Export Notes and Attachments from Salesforce

optional arguments:
  -h, --help            show this help message and exit
  -q query, --query query
                        SOQL to limit the valid Ids. Must
                        return the Id of related/parent objects.
```

## Example
```
python download.py -q 
"SELECT Id FROM Custom_Object__c WHERE Status__c = 'Approved'"
```

## Bug free software?

Probably not, feel free to report/fix any bugs. Thank you!