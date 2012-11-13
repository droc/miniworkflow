import pika
import simplejson

class WorkflowEventPublisher(object):
    def __init__(self, exchange):
        self.exchange = exchange
        self.__channel = None
        self.__connection = None

    def notify(self, event, node):
        message = {'event': event, 'data': node.description}
        serialized_message = simplejson.dumps(message)

        self.get_channel().basic_publish(exchange=self.exchange,
            routing_key='',
            body=serialized_message)
#        print " [x] Sent %r" % (message,)

    def shutdown(self):
        self.__connection.close()

    def get_channel(self):
        if not self.__channel:
            self.__connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
            self.__channel = self.__connection.channel()

            self.__channel.exchange_declare(exchange=self.exchange, exchange_type='fanout')
        return self.__channel