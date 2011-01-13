from slavealloc import exceptions
from slavealloc.data import queries, model

class Allocation(object):
    """
    
    A container class to hold all of the information necessary to make an allocation
    
    @ivar slavename: the slave name
    @ivar slaveid: its slaveid
    @ivar disabled: true if this slave is disabled
    @ivar master_nickname: master's nickname
    @iver master_fqdn: master's hostname
    @ivar master_pb_port: master's slave pb_port
    @ivar slave_basedir: the slave's basedir
    @ivar slave_password: the slave's password
    @ivar masterid: the assigned masterid
    """

    slavename = slaveid = disabled = master_nickname = master_fqdn = None
    master_pb_port = slave_basedir = slave_password = masterid = None

    def __init__(self, slavename):
        self.slavename = slavename

        # slave info
        q = model.slaves.select(whereclause=(model.slaves.c.name == slavename))
        slave_row = q.execute().fetchone()
        if not slave_row:
            raise exceptions.NoAllocationError
        self.slaveid = slave_row.slaveid
        self.disabled = slave_row.disabled
        self.slave_basedir = slave_row.basedir

        # bail out early if this slave is disabled
        if self.disabled:
            return

        # slave password
        q = queries.slave_password
        self.slave_password = q.execute(slaveid=self.slaveid).scalar()

        # if this slave has a locked_masterid, just get that row; otherwise, run
        # the self algorithm
        if slave_row.locked_masterid:
            q = model.masters.select(whereclause=(
                model.masters.c.masterid == slave_row.locked_masterid))
            master_row = q.execute().fetchone()
        else:
            # TODO: use slaveid, lose a join
            q = queries.best_master
            master_row = q.execute(slaveid=self.slaveid).fetchone()

        if not master_row:
            raise exceptions.NoAllocationError
        self.master_nickname = master_row.nickname
        self.master_fqdn = master_row.fqdn
        self.master_pb_port = master_row.pb_port
        self.masterid = master_row.masterid

    def commit(self):
        """
        Commit this allocation to the database
        """
        # note that this will work correctly for disabled slaves
        q = model.slaves.update(whereclause=(model.slaves.c.slaveid == self.slaveid),
                            values=dict(current_masterid=self.masterid))
        q.execute()

