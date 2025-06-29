# -*- coding: utf-8 -*-
# from odoo import http


# class BinauralQa(http.Controller):
#     @http.route('/binaural_qa/binaural_qa', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/binaural_qa/binaural_qa/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('binaural_qa.listing', {
#             'root': '/binaural_qa/binaural_qa',
#             'objects': http.request.env['binaural_qa.binaural_qa'].search([]),
#         })

#     @http.route('/binaural_qa/binaural_qa/objects/<model("binaural_qa.binaural_qa"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('binaural_qa.object', {
#             'object': obj
#         })

