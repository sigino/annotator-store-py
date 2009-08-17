import os
import shutil
import tempfile
import commands
from StringIO import StringIO

import annotater.model as model
model.set_default_connection()
model.createdb()
import annotater.store

class TestMapper:

    service_path = '/.annotation-xyz'
    store = annotater.store.AnnotaterStore(service_path=service_path)
    map = store.get_routes_mapper()

    def test_match_double_slash(self):
        # demonstrate that double slashes mess things up!
        self.map.environ = { 'REQUEST_METHOD' : 'GET' }
        out = self.map.match('//annotation/')
        assert out == None
        # assert out['action'] == 'index'

    def test_match_new(self):
        self.map.environ = { 'REQUEST_METHOD' : 'GET' }
        out = self.map.match('%s/annotation/new' % self.service_path)
        assert out['action'] == 'new'

    def test_match_index(self):
        self.map.environ = { 'REQUEST_METHOD' : 'GET' }
        out = self.map.match('%s/annotation' % self.service_path)
        assert out['action'] == 'index'

    def test_match_show(self):
        self.map.environ = { 'REQUEST_METHOD' : 'GET' }
        out = self.map.match('%s/annotation/1' % self.service_path)
        assert out['action'] == 'show'

    def test_match_create(self):
        self.map.environ = { 'REQUEST_METHOD' : 'POST' }
        out = self.map.match('%s/annotation' % self.service_path)
        assert out['action'] == 'create'

    def test_match_delete(self):
        self.map.environ = { 'REQUEST_METHOD' : 'GET' }
        out = self.map.match('%s/annotation/delete/1' % self.service_path)
        assert out['action'] == 'delete'
        assert out['id'] == '1'
        self.map.environ = { 'REQUEST_METHOD' : 'DELETE' }
        out = self.map.match('%s/annotation/1' % self.service_path)
        assert out['action'] == 'delete'
        assert out['id'] == '1'
        out = self.map.match('%s/annotation/' % self.service_path)
        assert out['id'] == None

    def test_match_edit(self):
        self.map.environ = { 'REQUEST_METHOD' : 'GET' }
        out = self.map.match('%s/annotation/edit/1' % self.service_path)
        assert out['action'] == 'edit'
        assert out['id'] == '1'

    def test_match_update(self):
        self.map.environ = { 'REQUEST_METHOD' : 'PUT' }
        out = self.map.match('%s/annotation/1' % self.service_path)
        assert out['action'] == 'update'
        assert out['id'] == '1'
        self.map.environ = { 'REQUEST_METHOD' : 'POST' }
        out = self.map.match('%s/annotation/1' % self.service_path)
        assert out['action'] == 'update'

    def test_url_for_new(self):
        offset = self.map.generate(controller='annotation', action='new')
        exp = '%s/annotation/new' % self.service_path
        assert offset == exp

    def test_url_for_create(self):
        offset = self.map.generate(controller='annotation', action='create',
                method='POST' )
        exp = '%s/annotation' % self.service_path
        assert offset == exp

    def test_url_for_delete(self):
        offset = self.map.generate(controller='annotation',
                action='delete', id=1, method='GET' )
        exp = '%s/annotation/delete/1' % self.service_path
        assert offset == exp
        offset = self.map.generate(controller='annotation',
                action='delete', id=1, method='DELETE' )
        exp = '%s/annotation/1' % self.service_path
        assert offset == exp

    def test_url_for_edit(self):
        offset = self.map.generate(controller='annotation',
                action='edit', id=1, method='GET')
        exp = '%s/annotation/edit/1' % self.service_path
        assert offset == exp

    def test_url_for_update(self):
        offset = self.map.generate(controller='annotation',
                action='update', id=1, method='POST')
        exp = '%s/annotation/1' % self.service_path
        assert offset == exp, (offset, exp)


class TestAnnotaterStore(object):

    def __init__(self, *args, **kwargs):
        # from paste.deploy import loadapp
        # wsgiapp = loadapp('config:test.ini', relative_to=conf_dir)
        import paste.fixture
        wsgiapp = annotater.store.AnnotaterStore(service_path='/annotation-xyz')
        self.map = wsgiapp.get_routes_mapper()
        self.app = paste.fixture.TestApp(wsgiapp)

    # TODO: reinstate once json stuff is sorted out
    def _test_0_annotate_index(self):
        anno_id = self._create_annotation()
        print anno_id
        offset = self.map.generate(controller='annotation', action='index')
        print offset
        res = self.app.get(offset)
        anno = model.Annotation.query.get(anno_id)
        assert anno.url in res

    def test_1_annotate_index_atom(self):
        anno_id = self._create_annotation()
        offset = self.map.generate(controller='annotation', action='index')
        offset += '?format=atom'
        print offset
        res = self.app.get(offset)
        anno = model.Annotation.query.get(anno_id)
        assert anno.note in res, res
        assert anno.range in res
        exp1 = '<feed xmlns:ptr="http://www.geof.net/code/annotation/"'
        assert exp1 in res

    def test_annotate_show(self):
        anno_id = self._create_annotation()
        offset = self.map.generate(controller='annotation', action='show',
                id=anno_id)
        res = self.app.get(offset)
        anno = model.Annotation.query.get(anno_id)
        assert anno.note in res, res
        assert anno.range in res, res

    def test_annotate_create(self):
        model.rebuilddb()
        offset = self.map.generate(controller='annotation', action='create')
        note = u'any old thing'
        params = {'note': note, 'url': 'http://localhost/'}
        print offset
        res = self.app.post(offset, params)
        # TODO make this test more selective
        items = model.Annotation.query.all()
        items = list(items)
        assert len(items) == 1
        assert items[0].note == note

    def test_annotate_delete(self):
        anno_id = self._create_annotation()
        offset = self.map.generate(controller='annotation', action='delete',
                method='GET', id=anno_id)
        self.app.get(offset, '204')
        tmp = model.Annotation.query.get(anno_id)
        assert tmp is None
    
    def _create_annotation(self):
        anno = model.Annotation(
                url=u'http://xyz.com',
                range=u'1.0 2.0',
                note=u'blah note',
                )
        model.Session.commit()
        anno_id = anno.id
        model.Session.remove()
        return anno_id

    def test_annotate_update(self):
        anno_id = self._create_annotation()
        offset = self.map.generate(controller='annotation', action='update',
                id=anno_id)
        newnote = u'This is a NEW note, a NEW note I say.'
        params = { 'note': newnote }
        self.app.post(offset, params)
        model.Session.remove()
        anno = model.Annotation.query.get(anno_id)
        assert anno.note == newnote
    
    def test_not_found(self):
        offset = self.map.generate(controller='annotation')
        self.app.get(offset, '404')

    def _test_bad_request(self):
        offset = self.map.generate(controller='annotation', action='edit',
                method='GET')
        self.app.get(offset, '400')
        

