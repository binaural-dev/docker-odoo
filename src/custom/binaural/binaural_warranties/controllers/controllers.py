# -*- coding: utf-8 -*-
# from odoo import http


# class BinauralWarranties(http.Controller):
#     @http.route('/binaural_warranties/binaural_warranties', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/binaural_warranties/binaural_warranties/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('binaural_warranties.listing', {
#             'root': '/binaural_warranties/binaural_warranties',
#             'objects': http.request.env['binaural_warranties.binaural_warranties'].search([]),
#         })

#     @http.route('/binaural_warranties/binaural_warranties/objects/<model("binaural_warranties.binaural_warranties"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('binaural_warranties.object', {
#             'object': obj
#         })

