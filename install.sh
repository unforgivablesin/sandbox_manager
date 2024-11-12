#!/bin/bash

mkdir -pv /etc/SandboxManager

cp -r src /etc/SandboxManager
cp -r remove.py create.py launch.py /etc/SandboxManager

cat > "/usr/bin/sandbox-create" << EOF
#!/bin/bash

python3 /etc/SandboxManager/create.py "\$@"
EOF

cat > "/usr/bin/sandbox-launch" << EOF
#!/bin/bash

python3 /etc/SandboxManager/launch.py "\$@"
EOF

cat > "/usr/bin/sandbox-remove" << EOF
#!/bin/bash

python3 /etc/SandboxManager/remove.py "\$@"
EOF

chmod 755 /usr/bin/sandbox-create /usr/bin/sandbox-launch /usr/bin/sandbox-remove
