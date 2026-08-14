import cv2
from plate_color.cli import color_distribution, main
from tests.synth import plate_swatch

WHITE_BG = (235, 235, 235); DARK = (20, 20, 20)
YELLOW_BG = (30, 200, 220)


def test_color_distribution(tmp_path):
    p1 = tmp_path / "a.png"; p2 = tmp_path / "b.png"
    cv2.imwrite(str(p1), plate_swatch(WHITE_BG, DARK))
    cv2.imwrite(str(p2), plate_swatch(YELLOW_BG, DARK))
    dist = color_distribution([str(p1), str(p2)])
    assert dist["white"] == 1
    assert dist["yellow"] == 1


def test_main_runs(tmp_path, capsys):
    p = tmp_path / "a.png"
    cv2.imwrite(str(p), plate_swatch(WHITE_BG, DARK))
    rc = main([str(tmp_path / "*.png")])
    assert rc == 0
    assert "white" in capsys.readouterr().out
