# coding: utf8
# try something like
@auth.requires_membership('Admin')
def new():
    postform = SQLFORM(db.post)
    categorylist = db(db.category.id > 0).select()
    for category in categorylist:
        postform[0].append(XML(str(INPUT(_type="checkbox", _name="category", _value=category.id))+category.title))
    postform[0].append(DIV("Tags:", INPUT(_type="textbox", _name="tags", _size="50")))
    if postform.accepts(request.vars, session):
        if 'category' in request.vars:
            postedcategories = [int(postedcategory) for postedcategory in request.vars.category]
            for postedcategory in postedcategories:
                db.relations.insert(post=postform.vars.id, category=postedcategory, relationtype='category')
        if 'tags' in request.vars:
            for tag in request.vars.tags.split(", "):
                db.relations.insert(post=postform.vars.id, tag=tag, relationtype='tag')
        redirect(URL(r=request, f="view", args=postform.vars.id))
    return dict(postform=postform)

@auth.requires_membership('Admin')
def edit():
    postid = request.args(0)
    post = db(db.post.id == postid).select()[0]
    relations = post.relations.select()
    postcategories = [relation.category for relation in relations if relation.relationtype == 'category']
    posttags = [relation.tag for relation in relations if relation.relationtype == 'tag']
    editform = SQLFORM(db.post, post, deletable=True)
    categorylist = db(db.category.id > 0).select()
    for category in categorylist:
        checked = 1 if category.id in postcategories else 0
        editform[0].append(XML(str(INPUT(_type="checkbox", _name="category", _value=category.id, value=checked))+category.title))
    editform[0].append(DIV(XML("<strong>Tags:</strong>"), INPUT(_type="textbox", _name="tags", _size="50", _value=", ".join(posttags), _style="margin-left: 100px;")))
    if editform.accepts(request.vars, session):
        if 'category' in request.vars:
            postedcategories = [int(postedcategory) for postedcategory in request.vars.category]
            for postedcategory in postedcategories:
                if postedcategory not in postcategories:
                    db.relations.insert(post=postid, category=postedcategory, relationtype='category')
            for postcategory in postcategories:
                if postcategory not in postedcategories:
                    db((db.relations.category == postcategory)&(db.relations.post == postid)).delete()
        if 'tags' in request.vars:
            for tag in request.vars.tags.split(", "):
                if tag not in posttags:
                    db.relations.insert(post=postid, tag=tag, relationtype='tag')
            for posttag in posttags:
                if posttag not in request.vars.tags.split(", "):
                    db((db.relations.post == postid)&(db.relations.tag == posttag)).delete()
        redirect(URL(r=request, f="view", args=postid))
    return dict(editform=editform, post=post, posttags=posttags)

def view():
    postid = request.args(0)
    post = db(db.post.id == postid).select()[0]
    relations = db(db.relations.post == postid).select()
    categories = dict((relation.category.id, relation.category.title) for relation in relations if relation.relationtype == 'category')
    tags = [relation.tag for relation in relations if relation.relationtype == 'tag']
    db.comment.post.default = postid
    commentform = SQLFORM(db.comment)
    if commentform.accepts(request.vars, session):
        redirect(URL(r=request, f="view", args=postid))
    return dict(post=post, commentform=commentform, categories=categories, tags=tags)

@auth.requires_membership('Admin')
def manageposts():
    posts = db(db.post.id > 0).select()
    return dict(posts=posts)

@auth.requires_membership('Admin')
def deleteposts():
    for postid in request.vars.delete:
        db(db.post.id == int(postid)).delete()
        db(db.comment.post == int(postid)).delete()
        db(db.relations.post == int(postid)).delete()
    redirect(URL(r=request, f="manageposts"))
