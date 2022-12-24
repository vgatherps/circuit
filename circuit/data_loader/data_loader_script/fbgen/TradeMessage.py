# automatically generated by the FlatBuffers compiler, do not modify

# namespace: 

import flatbuffers
from flatbuffers.compat import import_numpy
np = import_numpy()

class TradeMessage(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAs(cls, buf, offset=0):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = TradeMessage()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def GetRootAsTradeMessage(cls, buf, offset=0):
        """This method is deprecated. Please switch to GetRootAs."""
        return cls.GetRootAs(buf, offset)
    # TradeMessage
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # TradeMessage
    def LocalTimeUs(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Int64Flags, o + self._tab.Pos)
        return 0

    # TradeMessage
    def Message(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            x = self._tab.Indirect(o + self._tab.Pos)
            from TradeUpdate import TradeUpdate
            obj = TradeUpdate()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

def TradeMessageStart(builder): builder.StartObject(2)
def Start(builder):
    return TradeMessageStart(builder)
def TradeMessageAddLocalTimeUs(builder, localTimeUs): builder.PrependInt64Slot(0, localTimeUs, 0)
def AddLocalTimeUs(builder, localTimeUs):
    return TradeMessageAddLocalTimeUs(builder, localTimeUs)
def TradeMessageAddMessage(builder, message): builder.PrependUOffsetTRelativeSlot(1, flatbuffers.number_types.UOffsetTFlags.py_type(message), 0)
def AddMessage(builder, message):
    return TradeMessageAddMessage(builder, message)
def TradeMessageEnd(builder): return builder.EndObject()
def End(builder):
    return TradeMessageEnd(builder)