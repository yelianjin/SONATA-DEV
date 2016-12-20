#!/usr/bin/env python
#  Author:
#  Arpit Gupta (arpitg@cs.princeton.edu)

import json, time
from multiprocessing.connection import Client

class SparkQuery(object):
    """
    Abstract SparkQuery Class
    """
    def __init__(self):
        self.fields = []
        self.keys = []
        self.values = []
        self.expr = ''

    def eval(self):
        """
        evaluate this policy
        :param ?
        :type pkt: ?
        :rtype: ?
        """
        return self.expr

    def compile(self):
        """
        compile this policy for stream processor
        """
        return 0

class Map(SparkQuery):
    def __init__(self, *args, **kwargs):
        map_dict = dict(*args, **kwargs)
        self.prev_fields = map_dict['prev_fields']
        self.keys = ()
        self.values = ()
        if 'keys' in map_dict:
            self.keys = map_dict['keys']

        if 'values' in map_dict:
            self.values = map_dict['values']
        print(self.keys, self.values)
        #self.fields = self.keys + self.values

    def compile(self):
        if len(self.values) != 0:
            expr = ('map(lambda ('+','.join(str(x) for x in self.prev_fields)+
                    '): (('+','.join(str(x) for x in self.keys)+
                    '),('+','.join(str(x) for x in self.values)+')))')
        else:
            expr = ('map(lambda ('+','.join(str(x) for x in self.prev_fields)+
                    '): (('+','.join(str(x) for x in self.keys)+
                    ')))')
        return expr

class Reduce(SparkQuery):
    def __init__(self, *args, **kwargs):
        map_dict = dict(*args, **kwargs)
        self.prev_fields = map_dict['prev_fields']
        self.values = map_dict['values']
        self.func = map_dict['func']
        #self.fields = self.prev_fields[:-1] + self.values
        #self.fields = tuple(set(self.fields).difference(set("1")))

    def compile(self):
        expr = ''
        if self.func == 'sum':
            expr += 'reduceByKey(lambda x,y: x+y)'
        return expr

class Distinct(SparkQuery):
    def __init__(self, *args, **kwargs):
        map_dict = dict(*args, **kwargs)
        self.prev_fields = map_dict['prev_fields']
        self.fields = self.prev_fields

    def compile(self):
        expr = 'distinct()'
        return expr

class Filter(SparkQuery):
    def __init__(self, *args, **kwargs):
        map_dict = dict(*args, **kwargs)
        self.prev_fields = map_dict['prev_fields']
        self.fields = self.prev_fields
        self.expr = map_dict['expr']

    def compile(self):
        expr = ('filter(lambda ('
                +','.join(str(x) for x in self.prev_fields)
                +'): '+self.expr+')')
        return expr

class PacketStream(SparkQuery):
    def __init__(self, id):
        self.basic_headers = ["qid", "ts", "te","sIP", "sPort","dIP", "dPort", "nBytes",
                              "proto", "sMac", "dMac"]
        self.fields = tuple(self.basic_headers)
        self.keys = tuple([self.basic_headers[0]])
        self.values = tuple(self.basic_headers[1:])
        self.fields = self.keys + self.values
        self.operators = []
        self.expr = 'In'
        self.qid = id

    def compile(self):
        expr_sp = ''
        for operator in self.operators:
            #print type(operator), operator.compile()
            expr_sp += '.'+operator.compile()

        return expr_sp[1:]

    def get_prev_fields(self):
        if len(self.operators) > 0:
            prev_fields = self.operators[-1].fields
        else:
            prev_fields = self.fields
        return prev_fields

    def map(self, *args, **kwargs):
        map_dict = dict(*args, **kwargs)
        prev_fields = map_dict['prev_fields']
        keys = map_dict['keys']
        values = tuple([])
        if 'values' in map_dict:
            values = map_dict['values']

        self.expr += '.Map('+','.join([x for x in keys])+')'
        operator = Map(prev_fields = prev_fields, keys=keys, values=values)
        self.operators.append(operator)
        return self

    def reduce(self, *args, **kwargs):
        map_dict = dict(*args, **kwargs)
        prev_fields = map_dict['prev_fields']
        func = map_dict['func']
        values = map_dict['values']
        self.expr += '.Reduce('+func+','+','.join([x for x in values])+')'
        operator = Reduce(prev_fields = prev_fields,
                          func = func,
                          values = values)
        self.operators.append(operator)
        return self

    def distinct(self, *args, **kwargs):
        self.expr += '.Distinct()'
        map_dict = dict(*args, **kwargs)
        prev_fields = map_dict['prev_fields']
        operator = Distinct(prev_fields = prev_fields)
        self.operators.append(operator)
        return self

    def filter(self, *args, **kwargs):
        map_dict = dict(*args, **kwargs)
        prev_fields = map_dict['prev_fields']
        expr = map_dict['expr']
        self.expr += '.Filter('+expr+')'
        operator = Filter(prev_fields = prev_fields, expr=expr)
        self.operators.append(operator)
        return self
