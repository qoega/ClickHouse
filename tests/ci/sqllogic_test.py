#!/usr/bin/env python3

import argparse
import csv
import logging
import os
import subprocess
import sys
import atexit

from github import Github

from env_helper import TEMP_PATH, REPO_COPY, REPORTS_PATH
from s3_helper import S3Helper
from get_robot_token import get_best_robot_token
from pr_info import FORCE_TESTS_LABEL, PRInfo
from build_download_helper import download_all_deb_packages
from download_release_packets import download_last_release
from upload_result_helper import upload_results
from docker_pull_helper import get_image_with_version
from commit_status_helper import (
    post_commit_status,
    get_commit,
    override_status,
    post_commit_status_to_file,
    update_mergeable_check,
)
from clickhouse_helper import (
    ClickHouseHelper,
    mark_flaky_tests,
    prepare_tests_results_for_clickhouse,
)
from stopwatch import Stopwatch
from rerun_helper import RerunHelper
from tee_popen import TeePopen


NO_CHANGES_MSG = "Nothing to run"
IMAGE_NAME = "clickhouse/sqllogic-test"


def get_run_command(
    builds_path,
    repo_tests_path,
    result_path,
    server_log_path,
    kill_timeout,
    additional_envs,
    image
):
    envs = [
        f"-e MAX_RUN_TIME={int(0.9 * kill_timeout)}",
    ]
    envs += [f"-e {e}" for e in additional_envs]

    env_str = " ".join(envs)

    return (
        f"docker run "
        f"--volume={builds_path}:/package_folder "
        f"--volume={repo_tests_path}:/usr/share/clickhouse-test "
        f"--volume={result_path}:/test_output "
        f"--volume={server_log_path}:/var/log/clickhouse-server "
        f"--cap-add=SYS_PTRACE {env_str} {image}"
    )


def __files_in_dir(dir_path):
    return [
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if os.path.isfile(os.path.join(dir_path, f))
    ]


def process_results(result_folder, server_log_path):
    test_results = []
    # Just upload all files from result_folder.
    # If task provides processed results, then it's responsible for content of result_folder.
    additional_files = []
    if os.path.exists(result_folder):
        additional_files.extend(__files_in_dir(result_folder))

    if os.path.exists(server_log_path):
        additional_files.extend(__files_in_dir(server_log_path))

    status_path = os.path.join(result_folder, "check_status.tsv")
    if not os.path.exists(status_path):
        logging.info("Files in result folder %s", os.listdir(result_folder))
        return "error", "Not found check_status.tsv", test_results, additional_files

    logging.info("Found check_status.tsv")
    with open(status_path, "r", encoding="utf-8") as status_file:
        status = list(csv.reader(status_file, delimiter="\t"))

    if len(status) != 1 or len(status[0]) != 2:
        logging.info("Files in result folder %s", os.listdir(result_folder))
        return "error", "Invalid check_status.tsv", test_results, additional_files
    state, description = status[0][0], status[0][1]

    results_path = os.path.join(result_folder, "test_results.tsv")
    if not os.path.exists(results_path):
        logging.info("Files in result folder %s", os.listdir(result_folder))
        return "error", "Not found test_results.tsv", test_results, additional_files

    logging.info("Found test_results.tsv")
    with open(results_path, "r", encoding="utf-8") as results_file:
        test_results = list(csv.reader(results_file, delimiter="\t"))

    if len(test_results) == 0:
        return "error", "Empty test_results.tsv", test_results, additional_files

    return state, description, test_results, additional_files


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("check_name")
    parser.add_argument("kill_timeout", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    stopwatch = Stopwatch()

    temp_path = TEMP_PATH
    repo_path = REPO_COPY
    reports_path = REPORTS_PATH

    args = parse_args()
    check_name = args.check_name
    kill_timeout = args.kill_timeout

    pr_info = PRInfo()
    gh = Github(get_best_robot_token(), per_page=100)

    rerun_helper = RerunHelper(gh, pr_info, check_name)
    if rerun_helper.is_already_finished_by_status():
        logging.info("Check is already finished according to github status, exiting")
        sys.exit(0)

    if not os.path.exists(temp_path):
        os.makedirs(temp_path)

    docker_image = get_image_with_version(reports_path, IMAGE_NAME)

    repo_tests_path = os.path.join(repo_path, "tests")

    packages_path = os.path.join(temp_path, "packages")
    if not os.path.exists(packages_path):
        os.makedirs(packages_path)

    download_all_deb_packages(check_name, reports_path, packages_path)

    server_log_path = os.path.join(temp_path, "server_log")
    if not os.path.exists(server_log_path):
        os.makedirs(server_log_path)

    result_path = os.path.join(temp_path, "result_path")
    if not os.path.exists(result_path):
        os.makedirs(result_path)

    run_log_path = os.path.join(result_path, "runlog.log")

    additional_envs = []

    run_command = get_run_command(  # run script inside docker
        packages_path,
        repo_tests_path,
        result_path,
        server_log_path,
        kill_timeout,
        additional_envs,
        docker_image,
    )
    logging.info("Going to run func tests: %s", run_command)

    with TeePopen(run_command, run_log_path) as process:
        retcode = process.wait()
        if retcode == 0:
            logging.info("Run successfully")
        else:
            logging.info("Run failed")

    subprocess.check_call(f"sudo chown -R ubuntu:ubuntu {temp_path}", shell=True)

    return

    s3_helper = S3Helper()

    state, description, test_results, additional_logs = process_results(
        result_path, server_log_path
    )
    state = override_status(state, check_name)

    report_url = upload_results(
        s3_helper,
        pr_info.number,
        pr_info.sha,
        test_results,
        [run_log_path] + additional_logs,
        check_name,
    )

    print(f"::notice:: {check_name} Report url: {report_url}")

    if state != "success":
        if FORCE_TESTS_LABEL in pr_info.labels:
            print(f"'{FORCE_TESTS_LABEL}' enabled, will report success")
        else:
            sys.exit(1)
