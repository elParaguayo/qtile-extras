import textwrap


def test_absolute_layout(manager):
    layout = textwrap.dedent("""
        from qtile_extras.popup.toolkit import PopupAbsoluteLayout, PopupText
        self.popup = PopupAbsoluteLayout(
            self,
            controls=[
                PopupText(
                    "Test",
                    pos_x=10,
                    pos_y=10,
                    width=100,
                    height=100
                )
            ]
        )

        self.popup.show()
    """)
    manager.c.eval(layout)
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    control = info["controls"][0]
    assert control["x"] == 10
    assert control["y"] == 10
    assert control["width"] == 100
    assert control["height"] == 100


def test_relative_layout(manager):
    layout = textwrap.dedent("""
        from qtile_extras.popup.toolkit import PopupRelativeLayout, PopupText
        self.popup = PopupRelativeLayout(
            self,
            controls=[
                PopupText(
                    "Test",
                    pos_x=0.1,
                    pos_y=0.2,
                    width=0.5,
                    height=0.6
                )
            ],
            margin=0
        )

        self.popup.show()
    """)
    manager.c.eval(layout)
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    control = info["controls"][0]
    assert control["x"] == 20
    assert control["y"] == 40
    assert control["width"] == 100
    assert control["height"] == 120


def test_grid_layout(manager):
    layout = textwrap.dedent("""
        from qtile_extras.popup.toolkit import PopupGridLayout, PopupText
        self.popup = PopupGridLayout(
            self,
            controls=[
                PopupText(
                    "Test",
                    row=0,
                    col=1,
                    row_span=2,
                    col_span=3,
                )
            ],
            margin=0,
            rows=4,
            cols=4
        )

        self.popup.show()
    """)
    manager.c.eval(layout)
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    control = info["controls"][0]
    assert control["x"] == 50
    assert control["y"] == 0
    assert control["width"] == 150
    assert control["height"] == 100
