import sys
import os

sys.path.insert(0, os.path.abspath('.'))

try:
    import app.main
    import app.modules.picking.models
    import app.modules.picking.schemas
    import app.modules.picking.service
    import app.modules.picking.repository
    import app.modules.picking.routes
    print("No circular imports detected during loading.")
except Exception as e:
    print(f"Error: {e}")
