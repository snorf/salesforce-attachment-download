import concurrent.futures
from simple_salesforce import Salesforce
import requests
import os.path
import csv
import logging


def split_into_batches(items, batch_size):
    full_list = list(items)
    for i in range(0, len(full_list), batch_size):
        yield full_list[i:i + batch_size]


def create_filename(title, record_id, output_directory):
    # Create filename
    bad_chars = [';', ':', '!', "*", '/', '\\', ' ', ',','?','>','<']
    clean_title = filter(lambda i: i not in bad_chars, title)
    clean_title = ''.join(list(clean_title))
    filename = "{0}{1}-{2}".format(output_directory, record_id, clean_title)
    return filename


ATTACHMENT = 'attachment'
NOTE = 'note'


def get_record_ids(sf, output_directory, query, object_type, sharetype='V', visibility='AllUsers'):
    # Locate/Create output directory
    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    if object_type == ATTACHMENT:
        results_path = output_directory + 'files.csv'
    elif object_type == NOTE:
        results_path = output_directory + 'content_notes.csv'
    else:
        results_path = output_directory + 'unknown.csv'

    record_ids = set()
    records = sf.query_all(query)

    # Save results file with file mapping and return ids
    with open(results_path, 'w', encoding='UTF-8', newline='') as results_csv:
        file_writer = csv.writer(results_csv, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        if object_type == ATTACHMENT:
            file_writer.writerow(
                ['FirstPublishLocationId', 'AttachmentId', 'VersionData', 'PathOnClient', 'Title', 'OwnerId',
                 'CreatedDate', 'CreatedById', 'LastModifiedDate'])
        elif object_type == NOTE:
            file_writer.writerow(
                ['LinkedEntityId', 'LegacyNoteId', 'Title', 'OwnerId', 'Content', 'CreatedDate', 'CreatedById',
                 'LastModifiedDate', 'ShareType', 'Visibility'])

        for content_document in records["records"]:
            record_ids.add(content_document["Id"])
            if object_type == ATTACHMENT:
                filename = create_filename(content_document["Name"],
                                           content_document["Id"],
                                           output_directory)
                file_writer.writerow(
                    [content_document["ParentId"], content_document["Id"], filename, filename,
                     content_document["Name"], content_document["OwnerId"], content_document['CreatedDate'],
                     content_document['CreatedById'], content_document['LastModifiedDate']])
            elif object_type == NOTE:
                filename = create_filename(content_document["Title"] + '.txt',
                                           content_document["Id"],
                                           output_directory)
                file_writer.writerow(
                    [content_document["ParentId"], content_document["Id"], content_document["Title"],
                     content_document["OwnerId"], filename, content_document['CreatedDate'],
                     content_document['CreatedById'], content_document['LastModifiedDate'],
                     sharetype, visibility])

    return record_ids


def download_attachment(args):
    record, output_directory, sf = args
    # Create filename
    filename = create_filename(record["Name"], record["Id"], output_directory)
    url = "https://%s%s%s/body" % (sf.sf_instance, '/services/data/v47.0/sobjects/Attachment/', record["Id"])
    logging.debug("Downloading from " + url)
    response = requests.get(url, headers={"Authorization": "OAuth " + sf.session_id,
                                          "Content-Type": "application/octet-stream"})

    if response.ok:
        # Save File
        with open(filename, "wb") as output_file:
            output_file.write(response.content)
        return "Saved file to %s" % filename
    else:
        return "Couldn't download %s" % url


def fetch_files(sf, query_string, output_directory, object_type, valid_record_ids=None, batch_size=100):
    # Divide the full list of files into batches of 100 ids
    batches = list(split_into_batches(valid_record_ids, batch_size))

    i = 0
    for batch in batches:

        i = i + 1
        logging.info("Processing batch {0}/{1}".format(i, len(batches)))
        batch_query = query_string + ' WHERE Id in (' + ",".join("'" + item + "'" for item in batch) + ')'
        query_response = sf.query(batch_query)
        records_to_process = len(query_response["records"])
        logging.debug("{0} Query found {1} results".format(object_type, records_to_process))

        extracted = 0

        if object_type == ATTACHMENT:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                args = ((record, output_directory, sf) for record in query_response["records"])
                for result in executor.map(download_attachment, args):
                    logging.debug(result)
        elif object_type == NOTE:
            for r in query_response["records"]:
                filename = create_filename(r["Title"] + '.txt', r["Id"], output_directory)
                with open(filename, "w") as output_file:
                    extracted += 1
                    if r["Body"]:
                        output_file.write(r["Body"])
                        logging.debug("(%d/%d): Saved blob to %s " % (extracted, records_to_process, filename))
                    else:
                        output_file.write("")
                        logging.debug("(%d/%d): Empty Body for %s" % (extracted, records_to_process, filename))

        logging.info('All files in batch {0} downloaded'.format(i))
    logging.info('All batches complete')


def main():
    import argparse
    import configparser

    parser = argparse.ArgumentParser(description='Export Notes & Attachments from Salesforce')
    parser.add_argument('-q', '--query', metavar='query', required=True,
                        help='SOQL to select records from where Attachments should be downloaded. Must return the '
                             'Id(s) of parent objects.')
    args = parser.parse_args()

    # Get settings from config file
    config = configparser.ConfigParser()
    config.read('download.ini')

    username = config['salesforce']['username']
    password = config['salesforce']['password']
    token = config['salesforce']['security_token']
    is_sandbox = config['salesforce']['connect_to_sandbox']
    download_attachments = config['salesforce']['download_attachments'] == 'True'
    download_notes = config['salesforce']['download_notes'] == 'True'
    batch_size = int(config['salesforce']['batch_size'])
    loglevel = logging.getLevelName(config['salesforce']['loglevel'])
    sharetype = logging.getLevelName(config['salesforce']['sharetype'])
    visibility = logging.getLevelName(config['salesforce']['visibility'])
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=loglevel)

    attachment_query = 'SELECT Id, ContentType, Description, Name, OwnerId, ParentId, CreatedById, CreatedDate, ' \
                       'LastModifiedDate FROM Attachment WHERE ParentId IN ({0})'.format(args.query)
    notes_query = 'SELECT Id, Title, OwnerId, ParentId, CreatedById, CreatedDate, LastModifiedDate ' \
                  'FROM Note WHERE ParentId IN ({0})'.format(args.query)
    output = config['salesforce']['output_dir']

    attachment_query_string = "SELECT Id, ContentType, Description, Name, OwnerId, ParentId FROM Attachment"
    note_query_string = "SELECT Id, Body, Title, OwnerId, ParentId FROM Note"

    domain = None
    if is_sandbox == 'True':
        domain = 'test'

    # Output
    logging.info('Export Attachments from Salesforce')
    logging.info('Username: ' + username)
    logging.info('Output directory: ' + output)

    # Connect
    sf = Salesforce(username=username, password=password, security_token=token, domain=domain)
    logging.debug("Connected successfully to {0}".format(sf.sf_instance))

    if attachment_query and download_attachments:
        logging.info("Querying to get Attachment Ids...")
        valid_record_ids = get_record_ids(sf=sf, output_directory=output, query=attachment_query,
                                          object_type=ATTACHMENT)
        logging.info("Found {0} total attachments".format(len(valid_record_ids)))
        fetch_files(sf=sf, query_string=attachment_query_string, valid_record_ids=valid_record_ids,
                    output_directory=output, object_type=ATTACHMENT, batch_size=batch_size)

    if notes_query and download_notes:
        logging.info("Querying to get Note Ids...")
        valid_record_ids = get_record_ids(sf=sf, output_directory=output, query=notes_query,
                                          object_type=NOTE, sharetype=sharetype, visibility=visibility)
        logging.info("Found {0} total notes".format(len(valid_record_ids)))
        fetch_files(sf=sf, query_string=note_query_string,
                    valid_record_ids=valid_record_ids,
                    output_directory=output, object_type=NOTE, batch_size=batch_size)


if __name__ == "__main__":
    main()
