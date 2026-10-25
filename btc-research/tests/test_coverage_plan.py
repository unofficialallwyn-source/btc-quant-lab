from src.coverage_plan import DAY, coverage, next_window
def test_coverage_and_gaps():
    stored=[{"start":2*DAY,"end":5*DAY},{"start":4*DAY,"end":7*DAY},{"start":0,"end":DAY}]
    found,gaps=coverage(stored,0,9*DAY)
    assert found==[(0,DAY),(2*DAY,7*DAY)]
    assert gaps==[(DAY,2*DAY),(7*DAY,9*DAY)]
def test_next_window_limits():
    assert next_window([],0,45*DAY)==(0,28*DAY)
    assert next_window([{"start":0,"end":30*DAY}],0,45*DAY)==(30*DAY,45*DAY)
    assert next_window([{"start":0,"end":DAY}],0,DAY) is None
