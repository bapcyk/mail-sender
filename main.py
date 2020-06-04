import argparse
import sys
import os
import log
import job


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
logger = None

def parse_command_line():
    parser = argparse.ArgumentParser(prog='Mails sender')
    parser.add_argument('-r', '--restart', help="Send from the start, don't resume", action="store_true")
    parser.add_argument('-d', '--job-dir', default='job0', help='Job directory')
    opts = parser.parse_args()
    # os.path.join() handles rel/abs paths as well
    opts.job_dir = os.path.join(SCRIPT_DIR, opts.job_dir)
    return opts


def main():
    global logger
    cl_opts = parse_command_line()
    log.setup(cl_opts.job_dir)
    logger = log.logger()
    logger.info('=== New session ===')
    j = job.Job(cl_opts.job_dir, cl_opts.restart)
    j.send_all()
    # print([x.body_text for x in j.maildata])


main()