from fracmaster_toolbox.utils.file_utils import save_perf_excel
import os
import tempfile

def test_save_perf_excel(tmp_path):
    data = {'WellA': [('01', 100.0, 200.0, 300.0)]}
    out = tmp_path / 'out.xlsx'
    save_perf_excel(data, str(out))
    assert out.exists()
