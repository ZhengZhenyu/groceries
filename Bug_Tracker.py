import sys
from launchpadlib.launchpad import Launchpad


def parse_args(args):
    project = args[1].lower()
    created = args[2]
    try:
        before = args[3]
    except Exception:
        before = None

    return {
        'project': project,
        'created': created,
        'before': before
    }


if __name__ == "__main__":
    vals = parse_args(sys.argv)
    cachedir = '/opt/.launchpadlib/cache'
    launchpad = Launchpad.login_anonymously(
        'Bug-tracker', 'production', cachedir, version='devel')

    project = launchpad.projects[vals['project']]
    bugs = project.searchTasks(status=['New', 'Triaged', 'Confirmed',
                                       'In Progress', 'Fix Committed',
                                       'Fix Released'],
                               created_since=vals['created'],
                               created_before=vals['before'],)
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

    start = vals['created']
    if vals['before']:
        end = vals['before']
    else:
        end = 'Current'
    print '\n======================================='
    print 'Project:   ' + vals['project'].capitalize()
    print '---------------------------------------'
    print 'Start from ' + start + ' to ' + end
    print '---------------------------------------'
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
