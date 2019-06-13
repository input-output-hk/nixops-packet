import sys
import subprocess

from distutils.core import setup, Command


setup(name='nixops-packet',
      version='@version@',
      description='NixOS cloud deployment tool, but for Packet.net',
      url='https://github.com/input-output-hk/nixops-packet',
      author='Samuel Leathers',
      author_email='samuel.leathers@iohk.io',
      packages=[ 'nixopspacket', 'nixopspacket.backends', 'nixopspacket.resources' ],
      entry_points={'nixops': ['packet = nixopspacket.plugin']},
      py_modules=['plugin']
)
