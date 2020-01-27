import subprocess


def ssh_command(user, identity, host, command):
    # TODO: osh1 specifies -o StrictHostKeyChecking=no. Should it be kept?
    # TODO: Escape embedded quotes in command
    buffer = (['ssh', host, '-i', identity, '-T', '-l', user, '"' + command + '"']
              if identity else
              ['ssh', host, '-T', '-l', user, '"' + command + '"'])
    return ' '.join(buffer)


def ssh(user, identity, host, command):
    outcome = subprocess.run(ssh_command(user, identity, host, command),
                             shell=True,
                             executable='/bin/bash',
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             universal_newlines=True)
    return outcome.returncode, outcome.stdout, outcome.stderr
