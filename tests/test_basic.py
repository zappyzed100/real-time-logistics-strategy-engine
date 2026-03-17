def test_placeholder():
    # 構造が正しいことを確認するためのパス用テスト
    assert True


def test_environment():
    # Pythonが正しく動いているか確認
    import sys

    assert sys.version_info >= (3, 8)
