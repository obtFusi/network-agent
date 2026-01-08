from tools.network.ping_sweep import PingSweepTool

def get_all_tools():
    """Registry: Alle verfügbaren Tools"""
    return [
        PingSweepTool(),
        # Neue Tools hier hinzufügen
    ]
