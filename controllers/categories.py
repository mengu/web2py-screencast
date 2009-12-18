# coding: utf8
# try something like
def view():
    categoryid = request.args(0)
    category = db(db.category.id == categoryid).select()[0]
    categoryposts = db((db.relations.category == categoryid)&(db.relations.post == db.post.id)).select(orderby=~db.post.id)
    return dict(categoryposts=categoryposts, category=category)
