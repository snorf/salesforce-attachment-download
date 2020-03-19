# salesforce-attachment-download

Python script to download Salesforce Notes & Attachments.
It's using ProcessPoolExecutor to run downloads in parallell which 
makes the experience nicer if you have a large number of files.

## Getting Started

Download the script, satisfy requirements.txt and you're good to go!

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