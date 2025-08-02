import subprocess as sp
import sys


def find_branch(repo_name, branch_type,
                git_lab):

    if not git_lab:
        repo_url = 'git@github.com:COMPANY/{}.git'.format(repo_name)
    else:
        repo_url = 'git@git.COMPANY.com:{}.git'.format(repo_name)
    branch_output = sp.check_output(['git', 'ls-remote', '--heads', repo_url]
                                    ).strip().decode('UTF-8')
    branch_output = branch_output.split('\t')

    for branch in branch_output:
        if branch_type in branch:
            branch = branch.split('/')
            print(branch[3].split()[0])


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Gets active release or hotfix version from branch')
    parser.add_argument('--repo_name', help='Repo to search for branches')
    parser.add_argument('--branch_type', help='Specify which branch type to look up')
    parser.add_argument('--git_lab', help='Defaults to false, set to indicate branch lookup on GitLab')
    parser.set_defaults(branch_type='release', git_lab=False)

    p = parser.parse_args()
    p.branch_type = "{}/".format(p.branch_type)
    find_branch(p.repo_name, p.branch_type,
                p.git_lab)
