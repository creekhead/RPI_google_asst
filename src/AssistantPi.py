
import os.path
activate_this = os.path.join(os.path.dirname(__file__), '../env/bin/activate_this.py')
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

import examples.voice.assistant_library_with_local_commands_demo as assistant
assistant.main()

