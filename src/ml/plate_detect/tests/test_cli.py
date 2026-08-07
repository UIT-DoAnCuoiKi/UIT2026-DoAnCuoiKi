from plate_detect.cli import main


def test_check_dry_run_returns_zero(tmp_path, raw_fixture, capsys):
    # dry-run must not require processed data to exist
    rc = main(["check", "--dry-run",
               "--raw-dir", str(raw_fixture),
               "--processed-dir", str(tmp_path / "proc")])
    assert rc == 0
    assert "dry-run" in capsys.readouterr().out.lower()


def test_prepare_then_check(tmp_path, raw_fixture):
    proc = str(tmp_path / "proc")
    rc1 = main(["prepare", "--raw-dir", str(raw_fixture), "--processed-dir", proc,
                "--dataset-yaml", str(tmp_path / "a.yaml"),
                "--split-dir", str(tmp_path / "split")])
    assert rc1 == 0
    rc2 = main(["check", "--processed-dir", proc])
    assert rc2 == 0


def test_unknown_subcommand_errors():
    try:
        main(["frobnicate"])
        assert False, "should have raised SystemExit"
    except SystemExit as e:
        assert e.code != 0


def test_help_documents_flag_ordering(capsys):
    """Epilog must tell users that global flags follow the subcommand."""
    try:
        main(["--help"])
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert "follow the subcommand" in out
