#!/usr/bin/env python3

"""
This script should use a very simple, functional programming style.
Avoid Jinja macros in favor of native Python functions.

Don't go overboard on code generation; use Python only to generate
content that can't be easily declared statically using CircleCI's YAML API.

Data declarations (e.g. the nested loops for defining the configuration matrix)
should be at the top of the file for easy updating.

See this comment for design rationale:
https://github.com/pytorch/vision/pull/1321#issuecomment-531033978
"""

import jinja2
import yaml
import os.path


ALL_PYTHON_VERSIONS = [
    "2.7",
    "3.5",
    "3.6",
    "3.7",
]

ALL_CUDA_VERSIONS = [
    "cu92",
    "cu100",
]


def get_applicable_os_list(btype):
    os_list = ["linux", "macos"]
    if btype != "wheel":
        os_list.append("win")
    return os_list


def get_unicode_variants(btype, python_version):
    return [False, True] if btype == "wheel" and python_version == "2.7" else [False]


def workflows(category, prefix='', indentation=6, prune_python_and_cuda=False):
    w = []
    for btype in ["wheel", "conda"]:
        for os_type in get_applicable_os_list(btype):

            python_versions = ALL_PYTHON_VERSIONS[-1:] if prune_python_and_cuda else ALL_PYTHON_VERSIONS
            for python_version in python_versions:

                cuda_subset = ALL_CUDA_VERSIONS[-1:] if prune_python_and_cuda else ALL_CUDA_VERSIONS

                # TODO allow Windows to run CUDA
                cuda_list = cuda_subset if os_type == "linux" else []

                for cu_version in (["cpu"] + cuda_list):
                    for unicode in get_unicode_variants(btype, python_version):
                        w += workflow_pair(category, btype, os_type, python_version, cu_version, unicode, prefix)

    return indent(indentation, w)


def workflow_pair(category, btype, os_type, python_version, cu_version, unicode, prefix=''):

    w = []
    unicode_suffix = "u" if unicode else ""
    python_descriptor = f"py{python_version}{unicode_suffix}"

    name_components = [prefix] if prefix else [] + [
        category,
        os_type,
        btype,
        python_descriptor,
        cu_version,
    ]

    base_workflow_name = "_".join(name_components)

    w.append(generate_base_workflow(base_workflow_name, python_version, cu_version, unicode, os_type, btype))

    return w


def generate_base_workflow(base_workflow_name, python_version, cu_version, unicode, os_type, btype):

    d = {
        "name": base_workflow_name,
        "python_version": python_version,
        "cu_version": cu_version,
    }

    if unicode:
        d["unicode_abi"] = '1'

    if cu_version == "cu92":
        d["wheel_docker_image"] = "soumith/manylinux-cuda92"

    job_name_pieces = [
        "binary",
        os_type,
        btype,
    ]

    if cu_version != "cpu" and btype == "conda":
        job_name_pieces.append("cuda")

    job_name = "_".join(job_name_pieces)

    return {job_name: d}


def generate_subdirectory_paths(parent_directory):
    """
    Generate the tests, one for each repo
    """
    current_directory = os.path.abspath(os.getcwd())
    print("current_directory:", current_directory)
    return sorted([
        os.path.normpath(os.path.join(parent_directory, o))
        for o in os.listdir(parent_directory)
        if os.path.isdir(os.path.join(parent_directory, o))
    ])


def gen_command_steps_for_subdir(subdir_path, description):

    example_subdirs = generate_subdirectory_paths(subdir_path)

    steps_list = []
    for testdir in example_subdirs:
        runner_cmd = os.path.join(testdir, "run.sh")
        testname = os.path.basename(testdir)
        steps_list.append({"run": {
            "name": "Example Test: " + testname,
            "command": runner_cmd,
        }})

    return {
        "description": description,
        "steps": steps_list,
    }


def gen_commands():

    commands_dict = {
        "run_pytorch_examples": gen_command_steps_for_subdir(
            "test_community_repos/examples",
            "PyTorch examples"),

        "run_external_projects": gen_command_steps_for_subdir(
            "test_community_repos/external_projects",
            "External projects"),
    }

    return indent(2, commands_dict)


def indent(indentation, data_list):
    return ("\n" + " " * indentation).join(yaml.dump(data_list).splitlines())


if __name__ == "__main__":
    d = os.path.dirname(__file__)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(d),
        lstrip_blocks=True,
        autoescape=False,
    )

    with open(os.path.join(d, 'config.yml'), 'w') as f:
        f.write(env.get_template('config.in.yml').render(
            workflows=workflows,
            gen_commands=gen_commands
        ))