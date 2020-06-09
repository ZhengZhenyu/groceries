import os
import time
import argparse


parser = argparse.ArgumentParser(
    description='The helper script used to run MiniLlapLocalDriverTests in batchs.'
)

parser.add_argument('--batch_size', metavar='<batch_size>',
                    dest='batch_size', required=True,
                    help='The size of each batch.'              
)
parser.add_argument('--test_dir', metavar='<test_dir>',
                    dest='test_dir', required=True,
                    help='The dir of tests.'              
)


if __name__ == "__main__":
    parsed_args =  parser.parse_args()
    batch_size = int(parsed_args.batch_size)
    test_dir = parsed_args.test_dir
    config = {}
    exclusion_q_files = []
    
    filePath = test_dir + '/ql/src/test/queries/clientpositive'
    exclusion_modules = ["mr.query.files", "minimr.query.files", "minillap.query.files", "minitez.query.files",
            "encrypted.query.files", "druid.query.files", "druid.kafka.query.files", "hive.kafka.query.files",
            "erasurecoding.only.query.files", "beeline.positive.include", "spark.only.query.files",
            "localSpark.only.query.files", "miniSparkOnYarn.only.query.files"]

    for root,dirs,files in os.walk(filePath):
        if root == filePath:
            all_tests = files

    config_file = open(test_dir + '/itests/src/test/resources/testconfiguration.properties', 'r')

    current_config = ''
    config_content = config_file.read()

    lines = config_content.split('\n')

    for line in lines:
        line = line.strip()
        if line == '' or line.startswith('#'):
            continue
        if '=' in line:
            if line[-1] == '\\':
                line = line[:-2]
            config[line] = []
            current_config = line
        else:
            if line[-1] == '\\':
                line = line[:-1]
            if line[-1] == ',':
                line = line[:-1]
            config[current_config].append(line)

    for key, value in config.items():
        if key in exclusion_modules:
            for test in value:
                if test not in exclusion_q_files:
                    exclusion_q_files.append(test)

    valid_q_files = []
    for qfile in all_tests:
        if qfile not in exclusion_q_files:
            valid_q_files.append(qfile)

    rounds = len(valid_q_files)//batch_size
    if len(valid_q_files) % batch_size != 0:
        rounds += 1

    for i in range(rounds):
        cmd1 = 'cd ' + test_dir + '/itests/qtest/'
        cmd2 = 'mvn test -Dtest=TestMiniLlapLocalCliDriver -Dsurefire.rerunFailingTestsCount=3 -Dqfile='
        qfile_list = ''
        for qfile in valid_q_files[batch_size * i: batch_size * (i + 1)]:
            qfile_list = qfile_list + qfile + ','
        qfile_list = qfile_list[:-1]
        cmd2 = cmd2 + qfile_list
        cmd = cmd1 + " && " + cmd2
        #os.system(cmd)
        print(cmd)
        time.sleep(5)
        post_cmd1 = 'mv ' + test_dir + '/itests/qtest/target/surefire-reports/TEST-org.apache.hadoop.hive.cli.TestMiniLlapLocalCliDriver.xml '
        post_cmd2 = 'mv ' + test_dir + '/itests/qtest/target/surefire-reports/TEST-org.apache.hadoop.hive.cli.TestMiniLlapLocalCliDriver.xml-' + str(i)
        print(post_cmd1 + post_cmd2)
        #os.system(post_cmd1 + post_cmd2)
        time.sleep(5)
    

    
