# -*- coding: utf-8 -*-
# from odoo import http


# class Binaural(http.Controller):
#     @http.route('/binaural/binaural', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/binaural/binaural/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('binaural.listing', {
#             'root': '/binaural/binaural',
#             'objects': http.request.env['binaural.binaural'].search([]),
#         })

#     @http.route('/binaural/binaural/objects/<model("binaural.binaural"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('binaural.object', {
#             'object': obj
#         })

