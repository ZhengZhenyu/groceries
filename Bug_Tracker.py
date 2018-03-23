import argparse
from launchpadlib.launchpad import Launchpad

parser = argparse.ArgumentParser(
    description='The Launchpad Bug Tracker: '
                'This script can be used to track bugs registered in'
                'launchpad.net.')


parser.add_argument('--project_name', metavar='<project_name>',
                    dest='project_name', required=True,
                    help='Project to Track')
parser.add_argument('--after', metavar='<created_since>',
                    dest='created_since', required=True,
                    help='To track bugs registered after ...',)
parser.add_argument('--before', metavar='<created_before>',
                    dest='created_before',
                    help='To track bugs registered before ...')
parser.add_argument('--tags', metavar='<tags>', dest='tags',
                    help='Comma separated strings for tags to search. '
                         'To exclude, prepend a `-`, e.g. `-unwanted_tag`,'
                         '`wanted_tag`. The tags are working in `or` '
                         'mechanism: a,b => a or b.')
parser.add_argument('--detail', action='store_true', default=False,
                    help='Show detailed results.')


if __name__ == "__main__":
    parsed_args = parser.parse_args()
    cachedir = '/opt/.launchpadlib/cache'
    launchpad = Launchpad.login_anonymously(
        'Bug-tracker', 'production', cachedir, version='devel')
    if parsed_args.tags:
        tags = parsed_args.tags.split(',')
    project = launchpad.projects[parsed_args.project_name.lower()]
    bugs = project.searchTasks(status=['New', 'Triaged', 'Confirmed',
                                       'In Progress', 'Fix Committed',
                                       'Fix Released'],
                               created_since=parsed_args.created_since,
                               created_before=parsed_args.created_before,
                               tags=tags)
    importance = {'Critical': 0,
                  'High': 0,
                  'Medium': 0,
                  'Low': 0,
                  'Wishlist': 0,
                  'Undecided': 0}
    status_dict = {
        'New': 0,
        'Triaged': 0,
        'Confirmed': 0,
        'In Progress': 0,
        'Fix Committed': 0,
        'Fix Released': 0
    }
    for bug in bugs:
        importance[bug.importance] += 1
        status_dict[bug.status] += 1

    start = parsed_args.created_since
    if parsed_args.created_before:
        end = parsed_args.created_before
    else:
        end = 'Current'
    print '\n======================================='
    print 'Project:   ' + parsed_args.project_name.capitalize()
    print '---------------------------------------'
    print 'Start from ' + start + ' to ' + end
    print '---------------------------------------'
    if parsed_args.tags:
        print 'Results are filtered with tags:'
        for tag in tags:
            print tag
        '---------------------------------------'
    print 'Total Bugs:     ' + str(len(bugs))
    print '---------------------------------------'
    print 'Importance:     '
    print 'Critical:       ' + str(importance['Critical'])
    print 'High:           ' + str(importance['High'])
    print 'Medium:         ' + str(importance['Medium'])
    print 'Low:            ' + str(importance['Low'])
    print 'Wishlist:       ' + str(importance['Wishlist'])
    print 'Undecided:      ' + str(importance['Undecided'])
    print '---------------------------------------'
    print 'Status:                      '
    print 'New:            ' + str(status_dict['New'])
    print 'Triaged:        ' + str(status_dict['Triaged'])
    print 'Confirmed:      ' + str(status_dict['Confirmed'])
    print 'In Progress:    ' + str(status_dict['In Progress'])
    print 'Fix Committed:  ' + str(status_dict['Fix Committed'])
    print 'Fix Released:   ' + str(status_dict['Fix Released'])
    print '========================================\n'
    if parsed_args.detail:
        print 'Bug Details:'
        for bug in bugs:
            print bug.web_link + '    ' + bug.importance + '    ' + bug.status
