from mbot.common.stringutils import StringUtils


def test_noisestr():
    assert StringUtils.noisestr('yee') == 'y****'
