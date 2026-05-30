def test_diagnostics_report():
    import pykms_diagnostics as diagnostics

    report = diagnostics.build_report()
    assert 'uptime_seconds' in report
    assert 'gunicorn' in report
    assert 'recommendations' in report
    assert isinstance(report['var_files'], list)
