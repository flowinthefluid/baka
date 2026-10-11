"""Public camera extraction, location navigation and station evidence."""
from urllib.parse import parse_qs

import pytest

from resources.lib.livestreams import catalog, model, route, webcam_extract as extract, webcam_geography as geo
from resources.lib.handler.ParameterHandler import ParameterHandler
from tools import build_world_webcams as builder


def test_skyline_cdn_is_not_resolved_relative_to_directory():
    media, _ = extract.extract("var config={source:'livee.m3u8?a=short-lived'};", 'https://www.skylinewebcams.com/en/webcam/view.html')
    assert [m['url'] for m in media] == ['https://hd-auth.skylinewebcams.com/live.m3u8?a=short-lived']


def test_earthcam_selects_requested_view_and_never_an_unrelated_camera():
    text = 'var json_base={"cam":{"north":{"stream":"https://media.test/n.m3u8"},"south":{"stream":"https://media.test/s.m3u8"}}};'
    assert extract.extract(text, 'https://www.earthcam.com/place/?cam=south')[0][0]['url'].endswith('/s.m3u8')
    assert extract.extract(text, 'https://www.earthcam.com/place/?cam=missing')[0] == []


def test_panorama_extracts_main_live_frame_and_ignores_nearby_thumbnails():
    text = '<meta property="og:image" content="https://media.test/preview.jpg"><img src="nearby.jpg"><div class="field field-name-field-cam field-type-image"><img src="https://archive.panoramablick.com/archive/123/2026/10/11/12/00.jpg"></div>'
    assert extract.extract(text, 'https://www.panoramablick.com/wetter-webcam/place.html')[0][0]['url'].endswith('/12/00.jpg')


@pytest.mark.parametrize('page,text,target', [
    ('https://worldcam.eu/webcams/camera', '<a href="/click/source?id=42">Operator</a>', 'https://worldcam.eu/click/source?id=42'),
    ('https://liveworldwebcams.com/view/', '<img src="/wp-content/uploads/preview.jpg"><a class="player-external-link" href="https://operator.test/live/">Live view</a>', 'https://operator.test/live/')])
def test_directory_follows_operator_and_does_not_play_a_preview(page, text, target):
    assert extract.extract(text, page)[0] == []
    def fetch(url):
        return (text, page) if url == page else ('<video><source src="https://media.test/live.m3u8"></video>', target)
    result = extract.resolve(page, fetch=fetch)
    assert result['url'] == 'https://media.test/live.m3u8'
    assert result['headers']['Referer'] == target


def test_embedded_youtube_delegates_to_official_addon():
    media, _ = extract.extract('<iframe src="https://www.youtube.com/embed/abcdefghijk"></iframe>', 'https://liveworldwebcams.com/view/')
    assert media[0]['url'] == 'plugin://plugin.video.youtube/play/?video_id=abcdefghijk'


def test_canmore_javascript_youtube_player_is_extracted():
    text="new YT.Player('live',{playerVars:{autoplay:1},videoId:'_0wPODlF9wU',host:'https://www.youtube-nocookie.com'});"
    assert extract.extract(text,'https://www.skylinewebcams.com/en/webcam/canada/view.html')[0][0]['url'].endswith('video_id=_0wPODlF9wU')


def test_failed_or_looping_embeds_have_a_bounded_fetch_budget():
    calls = []
    def fetch(url):
        calls.append(url)
        return '<iframe src="https://operator.test/' + str(len(calls)) + '"></iframe>', url
    assert extract.resolve('https://operator.test/start', fetch=fetch) is None
    assert len(calls) <= 4


def test_listing_respects_skyline_root_relative_base():
    text = '<a href="en/webcam/canada/alberta/canmore/canmore.html"><img alt="Canmore - Canada"></a>'
    assert builder.camera_links(text, 'https://www.skylinewebcams.com/en/webcam/canada.html', 'skyline') == {'https://www.skylinewebcams.com/en/webcam/canada/alberta/canmore/canmore.html': 'Canmore - Canada'}


@pytest.mark.parametrize('code,continent', [('us','north_america'),('ca','north_america'),('pa','north_america'),('cu','north_america'),('br','south_america'),('de','europe'),('jp','asia'),('za','africa'),('nz','oceania'),('aq','antarctica')])
def test_continents_include_central_america_and_caribbean(code, continent):
    assert geo.continent({'country':code}) == continent


def test_weather_requires_explicit_station_name_and_evidence():
    assert not geo.is_weather_station({'section':'weather','sources':[{'official':True}]})
    assert not geo.is_weather_station({'weather_station':{'official':True,'name':'Station'}})
    assert geo.is_weather_station({'weather_station':{'official':True,'name':'Station','operator':'Weather service','evidence_url':'https://operator.test/station/'}})


@pytest.mark.parametrize('channel_id', ['baka:webcam:us:barrow-observatory',
                                     'baka:webcam:aq:south-pole-observatory'])
def test_noaa_observatories_are_documented_weather_stations(channel_id):
    station = catalog.get_channel(channel_id)
    assert station is not None
    assert geo.is_weather_station(station)
    assert station['weather_station']['camera_evidence_url'] == station['canonical_url']
    assert station['coordinate_evidence_url'].startswith('https://gml.noaa.gov/')
    assert station in catalog.channels_by_section('weather')
    assert catalog.approved_sources(station)[0]['protocol'] == 'jpeg'


@pytest.mark.parametrize('station,directory', [('casey', 'casey'), ('davis', 'davis'),
                                            ('mawson', 'mawson'), ('macquarie-island', 'macca')])
def test_antarctic_station_resolves_its_current_image_not_timelapse(station, directory):
    page = 'https://www.antarctica.gov.au/operations/webcams/' + station + '/'
    image = 'https://images.antarctica.gov.au/webcams/' + directory + '/2026/10/11/current.jpg'
    document = ('<img src="https://images.antarctica.gov.au/webcams/other/archive.jpg">'
                '<video><source src="/timelapse.mp4"></video><img src="' + image + '">')
    media, links = extract.extract(document, page)
    assert [item['url'] for item in media] == [image]
    assert media[0]['protocol'] == 'jpeg'
    assert links == []
    assert extract.extract('<img src="/thumbnail.jpg"><source src="/timelapse.mp4">', page) == ([], [])


def _camera(cid, url, genres, directory):
    return model.normalize_channel({'id':cid,'name':'The view','publisher':directory,'canonical_url':url,'section':'webcam','country':'ca','city':'Canmore','genre':genres,'directory_urls':['https://'+directory+'.test/view/'],'nsfw':False,'sources':[{'url':'https://'+directory+'.test/view/','resolver':'webcam_page','source_id':cid,'official':True}]})


def test_same_public_player_keeps_multiple_themes_and_directory_provenance():
    merged = catalog._merge([_camera('a','plugin://plugin.video.youtube/play/?video_id=abcdefghijk',['rockies'],'one'),_camera('b','plugin://plugin.video.youtube/play/?video_id=abcdefghijk',['mountains','lake'],'two')])
    assert len(merged) == 1
    assert merged[0]['genre'] == ['rockies','mountains','lake']
    assert len(merged[0]['directory_urls']) == 2
    assert 'b' in merged[0]['alias_ids']


def test_different_views_with_same_name_remain_separate():
    assert len(catalog._merge([_camera('a','https://operator.test/north',['city'],'one'),_camera('b','https://operator.test/south',['city'],'one')])) == 2


def test_country_navigation_ignores_movie_country_preferences(monkeypatch):
    monkeypatch.setattr(route,'_filtered_channels',lambda p:[{'country':'ca'},{'country':'us'}])
    monkeypatch.setattr(route.contentgate,'get_visible_countries',lambda c:[])
    entries=[]
    monkeypatch.setattr(route,'_folder',lambda title,level,params,thumb: entries.append((level,params)))
    p=ParameterHandler();p.setParam('section','webcam');p.setParam('continent','north_america')
    route._countries(p)
    assert {e[1]['country'] for e in entries} == {'ca','us'}
    assert all(e[0]=='cities' for e in entries)
    assert all(entry[1]['continent'] == 'north_america' for entry in entries)


@pytest.mark.parametrize('channel_id', ['baka:webcam:aq:casey-station', 'baka:webcam:aq:davis-station',
                                     'baka:webcam:aq:mawson-station', 'baka:webcam:au:macquarie-island-station'])
def test_australian_stations_use_documented_locations_and_current_page(channel_id):
    station = catalog.get_channel(channel_id)
    assert station in catalog.channels_by_section('weather')
    assert geo.is_weather_station(station)
    assert station['coordinates']['latitude'] < -50
    source = catalog.approved_sources(station)[0]
    assert source['resolver'] == 'webcam_page'
    assert source['url'] == station['weather_station']['camera_evidence_url']
    assert source['rights_evidence_url'].endswith('/copyright/')


def test_city_navigation_keeps_continent_country_and_city(monkeypatch):
    monkeypatch.setattr(route, '_filtered_channels', lambda params: [{'city': 'Canmore'}])
    entries = []
    monkeypatch.setattr(route, '_folder', lambda title, level, params, thumb: entries.append((level, params)))
    params = ParameterHandler()
    params.addParams({'section': 'webcam', 'continent': 'north_america', 'country': 'ca'})
    route._cities(params)
    assert entries == [('channels', {'section': 'webcam', 'continent': 'north_america',
                                    'country': 'ca', 'city': 'Canmore'})]


def test_resolved_headers_preserve_referer_query_values():
    source={'protocol':'hls','url':'https://media.test/live.m3u8','headers':{'Referer':'https://operator.test/?cam=a&view=b','User-Agent':'Mozilla/5.0'}}
    item=route._list_item_for({'name':'View'},source)
    assert parse_qs(item._props['inputstream.adaptive.stream_headers'])['Referer'] == ['https://operator.test/?cam=a&view=b']


def test_live_mjpeg_response_is_identified_without_buffering_the_infinite_body():
    class Response:
        headers={'Content-Type':'multipart/x-mixed-replace; boundary=frame'}
        url='https://operator.test/video'
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_content(self,**kwargs):raise AssertionError('Continuous body must not be read')
    class Session:
        def get(self,*args,**kwargs):
            assert kwargs['stream'] is True
            return Response()
    result=extract.fetch_page('https://operator.test/video',session=Session())
    assert result['protocol']=='mjpeg'
    assert extract.resolve('https://operator.test/video',fetch=lambda url:result)==result


def test_unresolved_first_source_still_resolves_the_directory_request(monkeypatch):
    sources=[{'source_id':'broken','url':'https://operator.test/broken','resolver':'webcam_page','protocol':'hls'},
             {'source_id':'working','url':'https://operator.test/working','resolver':'webcam_page','protocol':'hls'}]
    monkeypatch.setattr(catalog,'approved_sources',lambda channel:sources)
    monkeypatch.setattr(route.selector,'order_sources',lambda channel,approved:approved)
    monkeypatch.setattr(extract,'resolve_source',lambda source:None if source['source_id']=='broken' else dict(source,url='https://media.test/live.m3u8'))
    from types import SimpleNamespace
    monkeypatch.setattr(route,'cGui',lambda:SimpleNamespace(pluginHandle=7))
    from resources.lib.player import cPlayer
    monkeypatch.setattr(cPlayer,'startPlayer',lambda self:True)
    monkeypatch.setattr(route.selector,'mark_ok',lambda *args:None)
    calls=[]
    monkeypatch.setattr(route.xbmcplugin,'setResolvedUrl',lambda *args:calls.append(args))
    assert route._play_channel({'id':'view','name':'View'})
    assert calls[0][0:2]==(7,True)
    assert calls[0][2].getPath()=='https://media.test/live.m3u8'


def test_liveworld_historical_category_is_not_imported_as_a_camera():
    import json
    class Fetch:
        def get(self,url):
            if 'categories?' in url:
                values=[{'id':1,'name':'Time Travel','slug':'time-travel','parent':0},
                        {'id':2,'name':'Canada','slug':'canada','parent':0}]
            else:
                values=[{'link':'https://liveworldwebcams.com/titanic/','title':{'rendered':'RMS Titanic in color'},'content':{'rendered':''},'categories':[1]},
                        {'link':'https://liveworldwebcams.com/canmore/','title':{'rendered':'Canmore Webcam'},'content':{'rendered':''},'categories':[2]}]
            return {'text':json.dumps(values),'pages':1}
    records=builder.discover_liveworld(Fetch())
    assert len(records)==1 and records[0]['country']=='ca'
