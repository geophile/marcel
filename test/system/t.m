import os
(f'{os.getpid()} BEFORE')
bash marcel <<EOF
import os
(f'{os.getpid()} hi')
(f'{os.getpid()} bye')
EOF
(f'{os.getpid()} AFTER')

