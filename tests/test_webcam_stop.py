# -*- coding: utf-8 -*-
"""Closing a JPEG webcam must end its refresh loop without reopening it."""

import time

import pytest

from resources.lib.config import cConfig
from resources.lib.livestreams import route


@pytest.fixture
def picture_viewer(monkeypatch):
    state = {'time': 0.0, 'active': False, 'close_at': None,
             'abort_at': 20.0, 'pictures': [], 'waits': []}

    def execute(command, wait=False):
        if command.startswith('ShowPicture('):
            state['pictures'].append((state['time'], wait))
            state['active'] = True

    def visible(condition):
        assert condition == 'Window.IsActive(slideshow)'
        return state['active']

    class Monitor:
        def abortRequested(self):
            return state['time'] >= state['abort_at']

        def waitForAbort(self, timeout):
            assert timeout > 0
            state['waits'].append(timeout)
            state['time'] += timeout
            if state['close_at'] is not None and state['time'] >= state['close_at']:
                state['active'] = False
            return self.abortRequested()

    monkeypatch.setattr(route.xbmc, 'executebuiltin', execute)
    monkeypatch.setattr(route.xbmc, 'getCondVisibility', visible)
    monkeypatch.setattr(route.xbmc, 'Monitor', Monitor)
    monkeypatch.setattr(time, 'monotonic', lambda: state['time'])
    monkeypatch.setattr(route, '_notify', lambda _text: None)
    cConfig().setSetting('lsWebcamRefresh', '3')
    return state


def _show_camera():
    route._play_jpeg_slideshow({'name': 'Zugspitze'},
                               {'url': 'https://example.test/current.jpg'})


@pytest.mark.parametrize('close_at', [0.25, 2.75, 3.0])
def test_stop_or_back_never_reopens_webcam(picture_viewer, close_at):
    picture_viewer['close_at'] = close_at
    _show_camera()
    assert len(picture_viewer['pictures']) == 1
    assert picture_viewer['time'] <= close_at + 0.25
    assert max(picture_viewer['waits']) <= 0.25


def test_visible_webcam_refreshes_until_closed(picture_viewer):
    picture_viewer['close_at'] = 6.25
    _show_camera()
    assert [at for at, _wait in picture_viewer['pictures']] == [0, 3, 6]
    assert all(wait for _at, wait in picture_viewer['pictures'])
    assert picture_viewer['time'] == 6.25


def test_kodi_shutdown_stops_webcam_refresh(picture_viewer):
    picture_viewer['abort_at'] = 1.0
    _show_camera()
    assert len(picture_viewer['pictures']) == 1
    assert picture_viewer['time'] == 1.0


def test_already_shutting_down_does_not_open_webcam(picture_viewer):
    picture_viewer['abort_at'] = 0
    _show_camera()
    assert picture_viewer['pictures'] == []


def test_stop_during_current_image_resolution_does_not_reopen(picture_viewer, monkeypatch):
    from resources.lib.livestreams import webcam_extract
    def refresh(_page):
        picture_viewer['active'] = False
        return {'url':'https://camera.test/new.jpg','protocol':'jpeg'}
    monkeypatch.setattr(webcam_extract, 'resolve', refresh)
    route._play_jpeg_slideshow({'name':'View'}, {'url':'https://camera.test/old.jpg','resolver_page':'https://camera.test/page'})
    assert len(picture_viewer['pictures']) == 1
