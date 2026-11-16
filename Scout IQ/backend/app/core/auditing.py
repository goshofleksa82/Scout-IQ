from sqlalchemy import event,text
from sqlalchemy.orm import Session


def set_actor(db,user_id):
    db.info['audit_actor_id']=user_id
    db.execute(text("SELECT set_config('scoutiq.actor_id', :actor, true)"),{'actor':str(user_id)})


@event.listens_for(Session,'after_begin')
def transaction_actor(session,transaction,connection):
    actor=session.info.get('audit_actor_id')
    if actor is not None: connection.execute(text("SELECT set_config('scoutiq.actor_id', :actor, true)"),{'actor':str(actor)})
