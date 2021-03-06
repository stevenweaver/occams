# -*- coding: utf-8 -*-


class TestWriteData:

    def test_unicode(self, dbsession):
        """
        It should be able to export unicode strings
        """
        from contextlib import closing
        import six
        from sqlalchemy import literal_column, Integer, Unicode
        from occams import exports

        query = dbsession.query(
            literal_column(u"'420'", Integer).label(u'anumeric'),
            literal_column(u"'¿Qué pasa?'", Unicode).label(u'astring'),
            )

        with closing(six.BytesIO()) as fp:
            exports.write_data(fp, query)
            fp.seek(0)
            rows = [r for r in exports.csv.reader(fp)]

        assert sorted(['anumeric', 'astring']) == sorted(rows[0])
        assert sorted([u'420', u'¿Qué pasa?']) == sorted(rows[1])


class TestDumpCodeBook:

    def test_header(self, dbsession):
        """
        It should have the standard codebook header.
        """
        from contextlib import closing
        import six
        from occams import exports

        with closing(six.BytesIO()) as fp:
            exports.write_codebook(fp, [])
            fp.seek(0)
            fieldnames = exports.csv.DictReader(fp).fieldnames

        assert sorted(fieldnames) == sorted(exports.codebook.HEADER)
