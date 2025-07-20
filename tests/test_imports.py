import importlib

def test_imports():
    assert importlib.import_module('fracmaster_toolbox')
    assert importlib.import_module('fracmaster_toolbox.gui.main_gui')
    assert importlib.import_module('fracmaster_toolbox.job_setup.job_setup')
    assert importlib.import_module('fracmaster_toolbox.perf_converter.perf_converter')
    assert importlib.import_module('fracmaster_toolbox.packet_assist.packet_assistant')
