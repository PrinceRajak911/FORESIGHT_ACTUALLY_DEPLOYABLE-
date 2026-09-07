from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from forecasting import wape, bias

def test_wape_zero_error():
    assert wape(pd.Series([1,2,3]), pd.Series([1,2,3])) == 0

def test_bias_sign():
    assert bias(pd.Series([10,10]), pd.Series([12,8])) == 0
