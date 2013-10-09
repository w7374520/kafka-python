import logging
import unittest
import time
from datetime import datetime
import string
import random

from kafka import *  # noqa
from kafka.common import *  # noqa
from kafka.codec import has_gzip, has_snappy
from .fixtures import ZookeeperFixture, KafkaFixture


class TestKafkaClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):  # noqa
        cls.zk = ZookeeperFixture.instance()
        cls.server = KafkaFixture.instance(0, cls.zk.host, cls.zk.port)
        cls.client = KafkaClient(cls.server.host, cls.server.port)

    @classmethod
    def tearDownClass(cls):  # noqa
        cls.client.close()
        cls.server.close()
        cls.zk.close()

    #####################
    #   Produce Tests   #
    #####################

    def test_produce_many_simple(self):
        produce = ProduceRequest("test_produce_many_simple", 0, messages=[
            create_message("Test message %d" % i) for i in range(100)
        ])

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        (offset, ) = self.client.send_offset_request([OffsetRequest("test_produce_many_simple", 0, -1, 1)])
        self.assertEquals(offset.offsets[0], 100)

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 100)

        (offset, ) = self.client.send_offset_request([OffsetRequest("test_produce_many_simple", 0, -1, 1)])
        self.assertEquals(offset.offsets[0], 200)

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 200)

        (offset, ) = self.client.send_offset_request([OffsetRequest("test_produce_many_simple", 0, -1, 1)])
        self.assertEquals(offset.offsets[0], 300)

    def test_produce_10k_simple(self):
        produce = ProduceRequest("test_produce_10k_simple", 0, messages=[
            create_message("Test message %d" % i) for i in range(10000)
        ])

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        (offset, ) = self.client.send_offset_request([OffsetRequest("test_produce_10k_simple", 0, -1, 1)])
        self.assertEquals(offset.offsets[0], 10000)

    def test_produce_many_gzip(self):
        if not has_gzip():
            return
        message1 = create_gzip_message(["Gzipped 1 %d" % i for i in range(100)])
        message2 = create_gzip_message(["Gzipped 2 %d" % i for i in range(100)])

        produce = ProduceRequest("test_produce_many_gzip", 0, messages=[message1, message2])

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        (offset, ) = self.client.send_offset_request([OffsetRequest("test_produce_many_gzip", 0, -1, 1)])
        self.assertEquals(offset.offsets[0], 200)

    def test_produce_many_snappy(self):
        if not has_snappy():
            return
        message1 = create_snappy_message(["Snappy 1 %d" % i for i in range(100)])
        message2 = create_snappy_message(["Snappy 2 %d" % i for i in range(100)])

        produce = ProduceRequest("test_produce_many_snappy", 0, messages=[message1, message2])

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        (offset, ) = self.client.send_offset_request([OffsetRequest("test_produce_many_snappy", 0, -1, 1)])
        self.assertEquals(offset.offsets[0], 200)

    def test_produce_mixed(self):
        if not has_gzip() or not has_snappy():
            return
        message1 = create_message("Just a plain message")
        message2 = create_gzip_message(["Gzipped %d" % i for i in range(100)])
        message3 = create_snappy_message(["Snappy %d" % i for i in range(100)])

        produce = ProduceRequest("test_produce_mixed", 0, messages=[message1, message2, message3])

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        (offset, ) = self.client.send_offset_request([OffsetRequest("test_produce_mixed", 0, -1, 1)])
        self.assertEquals(offset.offsets[0], 201)

    def test_produce_100k_gzipped(self):
        req1 = ProduceRequest("test_produce_100k_gzipped", 0, messages=[
            create_gzip_message(["Gzipped batch 1, message %d" % i for i in range(50000)])
        ])

        for resp in self.client.send_produce_request([req1]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        (offset, ) = self.client.send_offset_request([OffsetRequest("test_produce_100k_gzipped", 0, -1, 1)])
        self.assertEquals(offset.offsets[0], 50000)

        req2 = ProduceRequest("test_produce_100k_gzipped", 0, messages=[
            create_gzip_message(["Gzipped batch 2, message %d" % i for i in range(50000)])
        ])

        for resp in self.client.send_produce_request([req2]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 50000)

        (offset, ) = self.client.send_offset_request([OffsetRequest("test_produce_100k_gzipped", 0, -1, 1)])
        self.assertEquals(offset.offsets[0], 100000)

    #####################
    #   Consume Tests   #
    #####################

    def test_consume_none(self):
        fetch = FetchRequest("test_consume_none", 0, 0, 1024)

        fetch_resp = self.client.send_fetch_request([fetch])[0]
        self.assertEquals(fetch_resp.error, 0)
        self.assertEquals(fetch_resp.topic, "test_consume_none")
        self.assertEquals(fetch_resp.partition, 0)

        messages = list(fetch_resp.messages)
        self.assertEquals(len(messages), 0)

    def test_produce_consume(self):
        produce = ProduceRequest("test_produce_consume", 0, messages=[
            create_message("Just a test message"),
            create_message("Message with a key", "foo"),
        ])

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        fetch = FetchRequest("test_produce_consume", 0, 0, 1024)

        fetch_resp = self.client.send_fetch_request([fetch])[0]
        self.assertEquals(fetch_resp.error, 0)

        messages = list(fetch_resp.messages)
        self.assertEquals(len(messages), 2)
        self.assertEquals(messages[0].offset, 0)
        self.assertEquals(messages[0].message.value, "Just a test message")
        self.assertEquals(messages[0].message.key, None)
        self.assertEquals(messages[1].offset, 1)
        self.assertEquals(messages[1].message.value, "Message with a key")
        self.assertEquals(messages[1].message.key, "foo")

    def test_produce_consume_many(self):
        produce = ProduceRequest("test_produce_consume_many", 0, messages=[
            create_message("Test message %d" % i) for i in range(100)
        ])

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        # 1024 is not enough for 100 messages...
        fetch1 = FetchRequest("test_produce_consume_many", 0, 0, 1024)

        (fetch_resp1,) = self.client.send_fetch_request([fetch1])

        self.assertEquals(fetch_resp1.error, 0)
        self.assertEquals(fetch_resp1.highwaterMark, 100)
        messages = list(fetch_resp1.messages)
        self.assertTrue(len(messages) < 100)

        # 10240 should be enough
        fetch2 = FetchRequest("test_produce_consume_many", 0, 0, 10240)
        (fetch_resp2,) = self.client.send_fetch_request([fetch2])

        self.assertEquals(fetch_resp2.error, 0)
        self.assertEquals(fetch_resp2.highwaterMark, 100)
        messages = list(fetch_resp2.messages)
        self.assertEquals(len(messages), 100)
        for i, message in enumerate(messages):
            self.assertEquals(message.offset, i)
            self.assertEquals(message.message.value, "Test message %d" % i)
            self.assertEquals(message.message.key, None)

    def test_produce_consume_two_partitions(self):
        produce1 = ProduceRequest("test_produce_consume_two_partitions", 0, messages=[
            create_message("Partition 0 %d" % i) for i in range(10)
        ])
        produce2 = ProduceRequest("test_produce_consume_two_partitions", 1, messages=[
            create_message("Partition 1 %d" % i) for i in range(10)
        ])

        for resp in self.client.send_produce_request([produce1, produce2]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        fetch1 = FetchRequest("test_produce_consume_two_partitions", 0, 0, 1024)
        fetch2 = FetchRequest("test_produce_consume_two_partitions", 1, 0, 1024)
        fetch_resp1, fetch_resp2 = self.client.send_fetch_request([fetch1, fetch2])
        self.assertEquals(fetch_resp1.error, 0)
        self.assertEquals(fetch_resp1.highwaterMark, 10)
        messages = list(fetch_resp1.messages)
        self.assertEquals(len(messages), 10)
        for i, message in enumerate(messages):
            self.assertEquals(message.offset, i)
            self.assertEquals(message.message.value, "Partition 0 %d" % i)
            self.assertEquals(message.message.key, None)
        self.assertEquals(fetch_resp2.error, 0)
        self.assertEquals(fetch_resp2.highwaterMark, 10)
        messages = list(fetch_resp2.messages)
        self.assertEquals(len(messages), 10)
        for i, message in enumerate(messages):
            self.assertEquals(message.offset, i)
            self.assertEquals(message.message.value, "Partition 1 %d" % i)
            self.assertEquals(message.message.key, None)

    ####################
    #   Offset Tests   #
    ####################

    @unittest.skip('commmit offset not supported in this version')
    def test_commit_fetch_offsets(self):
        req = OffsetCommitRequest("test_commit_fetch_offsets", 0, 42, "metadata")
        (resp,) = self.client.send_offset_commit_request("group", [req])
        self.assertEquals(resp.error, 0)

        req = OffsetFetchRequest("test_commit_fetch_offsets", 0)
        (resp,) = self.client.send_offset_fetch_request("group", [req])
        self.assertEquals(resp.error, 0)
        self.assertEquals(resp.offset, 42)
        self.assertEquals(resp.metadata, "")  # Metadata isn't stored for now

    # Producer Tests

    def test_simple_producer(self):
        producer = SimpleProducer(self.client, "test_simple_producer")
        resp = producer.send_messages("one", "two")

        # Will go to partition 0
        self.assertEquals(len(resp), 1)
        self.assertEquals(resp[0].error, 0)
        self.assertEquals(resp[0].offset, 0)    # offset of first msg

        # Will go to partition 1
        resp = producer.send_messages("three")
        self.assertEquals(len(resp), 1)
        self.assertEquals(resp[0].error, 0)
        self.assertEquals(resp[0].offset, 0)    # offset of first msg

        fetch1 = FetchRequest("test_simple_producer", 0, 0, 1024)
        fetch2 = FetchRequest("test_simple_producer", 1, 0, 1024)
        fetch_resp1, fetch_resp2 = self.client.send_fetch_request([fetch1,
                                                                   fetch2])
        self.assertEquals(fetch_resp1.error, 0)
        self.assertEquals(fetch_resp1.highwaterMark, 2)
        messages = list(fetch_resp1.messages)
        self.assertEquals(len(messages), 2)
        self.assertEquals(messages[0].message.value, "one")
        self.assertEquals(messages[1].message.value, "two")
        self.assertEquals(fetch_resp2.error, 0)
        self.assertEquals(fetch_resp2.highwaterMark, 1)
        messages = list(fetch_resp2.messages)
        self.assertEquals(len(messages), 1)
        self.assertEquals(messages[0].message.value, "three")

        # Will go to partition 0
        resp = producer.send_messages("four", "five")
        self.assertEquals(len(resp), 1)
        self.assertEquals(resp[0].error, 0)
        self.assertEquals(resp[0].offset, 2)    # offset of first msg

        producer.stop()

    def test_round_robin_partitioner(self):
        producer = KeyedProducer(self.client, "test_round_robin_partitioner",
                                 partitioner=RoundRobinPartitioner)
        producer.send("key1", "one")
        producer.send("key2", "two")
        producer.send("key3", "three")
        producer.send("key4", "four")

        fetch1 = FetchRequest("test_round_robin_partitioner", 0, 0, 1024)
        fetch2 = FetchRequest("test_round_robin_partitioner", 1, 0, 1024)

        fetch_resp1, fetch_resp2 = self.client.send_fetch_request([fetch1,
                                                                   fetch2])

        self.assertEquals(fetch_resp1.error, 0)
        self.assertEquals(fetch_resp1.highwaterMark, 2)
        self.assertEquals(fetch_resp1.partition, 0)

        messages = list(fetch_resp1.messages)
        self.assertEquals(len(messages), 2)
        self.assertEquals(messages[0].message.value, "one")
        self.assertEquals(messages[1].message.value, "three")

        self.assertEquals(fetch_resp2.error, 0)
        self.assertEquals(fetch_resp2.highwaterMark, 2)
        self.assertEquals(fetch_resp2.partition, 1)

        messages = list(fetch_resp2.messages)
        self.assertEquals(len(messages), 2)
        self.assertEquals(messages[0].message.value, "two")
        self.assertEquals(messages[1].message.value, "four")

        producer.stop()

    def test_hashed_partitioner(self):
        producer = KeyedProducer(self.client, "test_hash_partitioner",
                                 partitioner=HashedPartitioner)
        producer.send(1, "one")
        producer.send(2, "two")
        producer.send(3, "three")
        producer.send(4, "four")

        fetch1 = FetchRequest("test_hash_partitioner", 0, 0, 1024)
        fetch2 = FetchRequest("test_hash_partitioner", 1, 0, 1024)

        fetch_resp1, fetch_resp2 = self.client.send_fetch_request([fetch1,
                                                                   fetch2])

        self.assertEquals(fetch_resp1.error, 0)
        self.assertEquals(fetch_resp1.highwaterMark, 2)
        self.assertEquals(fetch_resp1.partition, 0)

        messages = list(fetch_resp1.messages)
        self.assertEquals(len(messages), 2)
        self.assertEquals(messages[0].message.value, "two")
        self.assertEquals(messages[1].message.value, "four")

        self.assertEquals(fetch_resp2.error, 0)
        self.assertEquals(fetch_resp2.highwaterMark, 2)
        self.assertEquals(fetch_resp2.partition, 1)

        messages = list(fetch_resp2.messages)
        self.assertEquals(len(messages), 2)
        self.assertEquals(messages[0].message.value, "one")
        self.assertEquals(messages[1].message.value, "three")

        producer.stop()

    def test_acks_none(self):
        producer = SimpleProducer(self.client, "test_acks_none",
                                  req_acks=SimpleProducer.ACK_NOT_REQUIRED)
        resp = producer.send_messages("one")
        self.assertEquals(len(resp), 0)

        fetch = FetchRequest("test_acks_none", 0, 0, 1024)
        fetch_resp = self.client.send_fetch_request([fetch])

        self.assertEquals(fetch_resp[0].error, 0)
        self.assertEquals(fetch_resp[0].highwaterMark, 1)
        self.assertEquals(fetch_resp[0].partition, 0)

        messages = list(fetch_resp[0].messages)
        self.assertEquals(len(messages), 1)
        self.assertEquals(messages[0].message.value, "one")

        producer.stop()

    def test_acks_local_write(self):
        producer = SimpleProducer(self.client, "test_acks_local_write",
                                  req_acks=SimpleProducer.ACK_AFTER_LOCAL_WRITE)
        resp = producer.send_messages("one")
        self.assertEquals(len(resp), 1)

        fetch = FetchRequest("test_acks_local_write", 0, 0, 1024)
        fetch_resp = self.client.send_fetch_request([fetch])

        self.assertEquals(fetch_resp[0].error, 0)
        self.assertEquals(fetch_resp[0].highwaterMark, 1)
        self.assertEquals(fetch_resp[0].partition, 0)

        messages = list(fetch_resp[0].messages)
        self.assertEquals(len(messages), 1)
        self.assertEquals(messages[0].message.value, "one")

        producer.stop()

    def test_acks_cluster_commit(self):
        producer = SimpleProducer(
            self.client, "test_acks_cluster_commit",
            req_acks=SimpleProducer.ACK_AFTER_CLUSTER_COMMIT)
        resp = producer.send_messages("one")
        self.assertEquals(len(resp), 1)

        fetch = FetchRequest("test_acks_cluster_commit", 0, 0, 1024)
        fetch_resp = self.client.send_fetch_request([fetch])

        self.assertEquals(fetch_resp[0].error, 0)
        self.assertEquals(fetch_resp[0].highwaterMark, 1)
        self.assertEquals(fetch_resp[0].partition, 0)

        messages = list(fetch_resp[0].messages)
        self.assertEquals(len(messages), 1)
        self.assertEquals(messages[0].message.value, "one")

        producer.stop()

    def test_async_simple_producer(self):
        producer = SimpleProducer(self.client, "test_async_simple_producer",
                                  async=True)

        resp = producer.send_messages("one")
        self.assertEquals(len(resp), 0)

        # Give it some time
        time.sleep(2)

        fetch = FetchRequest("test_async_simple_producer", 0, 0, 1024)
        fetch_resp = self.client.send_fetch_request([fetch])

        self.assertEquals(fetch_resp[0].error, 0)
        self.assertEquals(fetch_resp[0].highwaterMark, 1)
        self.assertEquals(fetch_resp[0].partition, 0)

        messages = list(fetch_resp[0].messages)
        self.assertEquals(len(messages), 1)
        self.assertEquals(messages[0].message.value, "one")

        producer.stop()

    def test_async_keyed_producer(self):
        producer = KeyedProducer(self.client, "test_async_keyed_producer",
                                 async=True)

        resp = producer.send("key1", "one")
        self.assertEquals(len(resp), 0)

        # Give it some time
        time.sleep(2)

        fetch = FetchRequest("test_async_keyed_producer", 0, 0, 1024)
        fetch_resp = self.client.send_fetch_request([fetch])

        self.assertEquals(fetch_resp[0].error, 0)
        self.assertEquals(fetch_resp[0].highwaterMark, 1)
        self.assertEquals(fetch_resp[0].partition, 0)

        messages = list(fetch_resp[0].messages)
        self.assertEquals(len(messages), 1)
        self.assertEquals(messages[0].message.value, "one")

        producer.stop()

    def test_batched_simple_producer(self):
        producer = SimpleProducer(self.client, "test_batched_simple_producer",
                                  batch_send=True,
                                  batch_send_every_n=10,
                                  batch_send_every_t=20)

        # Send 5 messages and do a fetch
        msgs = ["message-%d" % i for i in range(0, 5)]
        resp = producer.send_messages(*msgs)

        # Batch mode is async. No ack
        self.assertEquals(len(resp), 0)

        # Give it some time
        time.sleep(2)

        fetch1 = FetchRequest("test_batched_simple_producer", 0, 0, 1024)
        fetch2 = FetchRequest("test_batched_simple_producer", 1, 0, 1024)
        fetch_resp1, fetch_resp2 = self.client.send_fetch_request([fetch1,
                                                                   fetch2])

        self.assertEquals(fetch_resp1.error, 0)
        messages = list(fetch_resp1.messages)
        self.assertEquals(len(messages), 0)

        self.assertEquals(fetch_resp2.error, 0)
        messages = list(fetch_resp2.messages)
        self.assertEquals(len(messages), 0)

        # Send 5 more messages, wait for 2 seconds and do a fetch
        msgs = ["message-%d" % i for i in range(5, 10)]
        resp = producer.send_messages(*msgs)

        # Give it some time
        time.sleep(2)

        fetch1 = FetchRequest("test_batched_simple_producer", 0, 0, 1024)
        fetch2 = FetchRequest("test_batched_simple_producer", 1, 0, 1024)
        fetch_resp1, fetch_resp2 = self.client.send_fetch_request([fetch1,
                                                                   fetch2])

        self.assertEquals(fetch_resp1.error, 0)
        messages = list(fetch_resp1.messages)
        self.assertEquals(len(messages), 5)

        self.assertEquals(fetch_resp2.error, 0)
        messages = list(fetch_resp2.messages)
        self.assertEquals(len(messages), 5)

        # Send 7 messages and wait for 20 seconds
        msgs = ["message-%d" % i for i in range(10, 15)]
        resp = producer.send_messages(*msgs)
        msgs = ["message-%d" % i for i in range(15, 17)]
        resp = producer.send_messages(*msgs)

        fetch1 = FetchRequest("test_batched_simple_producer", 0, 5, 1024)
        fetch2 = FetchRequest("test_batched_simple_producer", 1, 5, 1024)
        fetch_resp1, fetch_resp2 = self.client.send_fetch_request([fetch1,
                                                                   fetch2])

        self.assertEquals(fetch_resp1.error, 0)
        self.assertEquals(fetch_resp2.error, 0)
        messages = list(fetch_resp1.messages) + list(fetch_resp2.messages)
        self.assertEquals(len(messages), 0)

        # Give it some time
        time.sleep(22)

        fetch1 = FetchRequest("test_batched_simple_producer", 0, 5, 1024)
        fetch2 = FetchRequest("test_batched_simple_producer", 1, 5, 1024)
        fetch_resp1, fetch_resp2 = self.client.send_fetch_request([fetch1,
                                                                   fetch2])

        self.assertEquals(fetch_resp1.error, 0)
        self.assertEquals(fetch_resp2.error, 0)
        messages = list(fetch_resp1.messages) + list(fetch_resp2.messages)
        self.assertEquals(len(messages), 7)

        producer.stop()


class TestConsumer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zk = ZookeeperFixture.instance()
        cls.server1 = KafkaFixture.instance(0, cls.zk.host, cls.zk.port)
        cls.server2 = KafkaFixture.instance(1, cls.zk.host, cls.zk.port)
        cls.client = KafkaClient(cls.server2.host, cls.server2.port, bufsize=8192)

    @classmethod
    def tearDownClass(cls):  # noqa
        cls.client.close()
        cls.server1.close()
        cls.server2.close()
        cls.zk.close()

    def test_simple_consumer(self, driver_type=KAFKA_PROCESS_DRIVER):
        queue = "test_simple_consumer_%s" % (driver_type)

        # Produce 100 messages to partition 0
        produce1 = ProduceRequest(queue, 0, messages=[
            create_message("Test message 0 %d" % i) for i in range(100)
        ])

        for resp in self.client.send_produce_request([produce1]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        # Produce 100 messages to partition 1
        produce2 = ProduceRequest(queue, 1, messages=[
            create_message("Test message 1 %d" % i) for i in range(100)
        ])

        for resp in self.client.send_produce_request([produce2]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        # Start a consumer
        consumer = SimpleConsumer(self.client, "group1", queue,
                                  auto_commit=False,
                                  driver_type=driver_type)

        all_messages = []
        for message in consumer:
            all_messages.append(message)

        self.assertEquals(len(all_messages), 200)
        # Make sure there are no duplicates
        self.assertEquals(len(all_messages), len(set(all_messages)))

        consumer.seek(-10, 2)
        all_messages = []
        for message in consumer:
            all_messages.append(message)

        self.assertEquals(len(all_messages), 10)

        consumer.seek(-13, 2)
        all_messages = []
        for message in consumer:
            all_messages.append(message)

        self.assertEquals(len(all_messages), 13)

        consumer.stop()

    def test_simple_consumer_blocking(self):
        consumer = SimpleConsumer(self.client, "group1", "test_simple_consumer_blocking", auto_commit=False)

        # Blocking API
        start = datetime.now()
        messages = consumer.get_messages(block=True, timeout=5)
        diff = (datetime.now() - start).total_seconds()
        self.assertGreaterEqual(diff, 5)
        self.assertEqual(len(messages), 0)

        # Send 10 messages
        produce = ProduceRequest(queue, 0, messages=[
            create_message("Test message 0 %d" % i) for i in range(10)
        ])

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        # Fetch 5 messages
        messages = consumer.get_messages(count=5, block=True, timeout=5)
        self.assertEqual(len(messages), 5)

        # Fetch 10 messages
        start = datetime.now()
        messages = consumer.get_messages(count=10, block=True, timeout=5)
        self.assertEqual(len(messages), 5)
        diff = (datetime.now() - start).total_seconds()
        self.assertGreaterEqual(diff, 5)

        consumer.stop()

    def test_simple_consumer_gevent(self):
        return self.test_simple_consumer(driver_type=KAFKA_GEVENT_DRIVER)

    def test_simple_consumer_thread(self):
        return self.test_simple_consumer(driver_type=KAFKA_THREAD_DRIVER)

    def test_simple_consumer_pending(self, driver_type=KAFKA_PROCESS_DRIVER):
        queue = "test_simple_pending_%s" % (driver_type)

        # Produce 10 messages to partition 0 and 1
        produce1 = ProduceRequest(queue, 0, messages=[
            create_message("Test message 0 %d" % i) for i in range(10)
        ])
        for resp in self.client.send_produce_request([produce1]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        produce2 = ProduceRequest(queue, 1, messages=[
            create_message("Test message 1 %d" % i) for i in range(10)
        ])
        for resp in self.client.send_produce_request([produce2]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        consumer = SimpleConsumer(self.client, "group1", queue,
                                  auto_commit=False,
                                  driver_type=driver_type)

        self.assertEquals(consumer.pending(), 20)
        self.assertEquals(consumer.pending(partitions=[0]), 10)
        self.assertEquals(consumer.pending(partitions=[1]), 10)
        consumer.stop()

    def test_simple_consumer_pending_gevent(self):
        return self.test_simple_consumer_pending(
                                    driver_type=KAFKA_GEVENT_DRIVER)

    def test_simple_consumer_pending_thread(self):
        return self.test_simple_consumer_pending(
                                    driver_type=KAFKA_THREAD_DRIVER)

    def test_multi_consumer(self, driver_type=KAFKA_PROCESS_DRIVER):
        queue = "test_mpconsumer_%s" % (driver_type)

        # Produce 100 messages to partition 0
        produce1 = ProduceRequest(queue, 0, messages=[
            create_message("Test message 0 %d" % i) for i in range(100)
        ])

        for resp in self.client.send_produce_request([produce1]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        # Produce 100 messages to partition 1
        produce2 = ProduceRequest(queue, 1, messages=[
            create_message("Test message 1 %d" % i) for i in range(100)
        ])

        for resp in self.client.send_produce_request([produce2]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        # Start a consumer
        consumer = MultiConsumer(self.client, "grp1", queue,
                                 auto_commit=False,
                                 driver_type=driver_type)

        all_messages = []
        for message in consumer:
            all_messages.append(message)

        self.assertEquals(len(all_messages), 200)
        # Make sure there are no duplicates
        self.assertEquals(len(all_messages), len(set(all_messages)))

        # Blocking API
        start = datetime.now()
        messages = consumer.get_messages(block=True, timeout=5)
        diff = (datetime.now() - start).total_seconds()
        self.assertGreaterEqual(diff, 5)
        self.assertEqual(len(messages), 0)

        # Send 10 messages
        produce = ProduceRequest(queue, 0, messages=[
            create_message("Test message 0 %d" % i) for i in range(10)
        ])

        for resp in self.client.send_produce_request([produce]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 100)

        # Fetch 5 messages
        messages = consumer.get_messages(count=5, block=True, timeout=5)
        self.assertEqual(len(messages), 5)

        # Fetch 10 messages
        start = datetime.now()
        messages = consumer.get_messages(count=10, block=True, timeout=5)
        self.assertEqual(len(messages), 5)
        diff = (datetime.now() - start).total_seconds()
        self.assertGreaterEqual(diff, 5)

        consumer.stop()

    def test_multi_consumer_gevent(self):
        return self.test_multi_consumer(driver_type=KAFKA_GEVENT_DRIVER)

    def test_multi_consumer_thread(self):
        return self.test_multi_consumer(driver_type=KAFKA_THREAD_DRIVER)

    def test_multi_proc_pending(self, driver_type=KAFKA_PROCESS_DRIVER):
        queue = "test_mppending_%s" % (driver_type)

        # Produce 10 messages to partition 0 and 1
        produce1 = ProduceRequest(queue, 0, messages=[
            create_message("Test message 0 %d" % i) for i in range(10)
        ])

        for resp in self.client.send_produce_request([produce1]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        produce2 = ProduceRequest(queue, 1, messages=[
            create_message("Test message 1 %d" % i) for i in range(10)
        ])

        for resp in self.client.send_produce_request([produce2]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        consumer = MultiConsumer(self.client, "group1", queue,
                                 auto_commit=False,
                                 driver_type=driver_type)

        self.assertEquals(consumer.pending(), 20)
        self.assertEquals(consumer.pending(partitions=[0]), 10)
        self.assertEquals(consumer.pending(partitions=[1]), 10)

        consumer.stop()

    def test_multi_proc_pending_gevent(self):
        return self.test_multi_proc_pending(driver_type=KAFKA_GEVENT_DRIVER)

    def test_multi_proc_pending_thread(self):
        return self.test_multi_proc_pending(driver_type=KAFKA_THREAD_DRIVER)

    def test_large_messages(self):
        # Produce 10 "normal" size messages
        messages1 = [create_message(random_string(1024)) for i in range(10)]
        produce1 = ProduceRequest("test_large_messages", 0, messages1)

        for resp in self.client.send_produce_request([produce1]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 0)

        # Produce 10 messages that are too large (bigger than default fetch size)
        messages2 = [create_message(random_string(5000)) for i in range(10)]
        produce2 = ProduceRequest("test_large_messages", 0, messages2)

        for resp in self.client.send_produce_request([produce2]):
            self.assertEquals(resp.error, 0)
            self.assertEquals(resp.offset, 10)

        # Consumer should still get all of them
        consumer = SimpleConsumer(self.client, "group1", "test_large_messages", auto_commit=False)
        all_messages = messages1 + messages2
        for i, message in enumerate(consumer):
            self.assertEquals(all_messages[i], message.message)
        self.assertEquals(i, 19)

class TestFailover(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        zk_chroot = random_string(10)
        replicas   = 2
        partitions = 2

        # mini zookeeper, 2 kafka brokers
        cls.zk      = ZookeeperFixture.instance()
        kk_args     = [cls.zk.host, cls.zk.port, zk_chroot, replicas, partitions]
        cls.brokers = [KafkaFixture.instance(i, *kk_args) for i in range(replicas)]
        cls.client  = KafkaClient(cls.brokers[0].host, cls.brokers[0].port)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        for broker in cls.brokers:
            broker.close()
        cls.zk.close()

    def test_switch_leader(self):

        key, topic, partition = random_string(5), 'test_switch_leader', 0
        producer = SimpleProducer(self.client, topic)

        for i in range(1, 4):

            # XXX unfortunately, the conns dict needs to be warmed for this to work
            # XXX unfortunately, for warming to work, we need at least as many partitions as brokers
            self._send_random_messages(producer, 10)

            # kil leader for partition 0
            broker = self._kill_leader(topic, partition)

            # expect failure, reload meta data
            with self.assertRaises(FailedPayloadsException):
                producer.send_messages('part 1')
                producer.send_messages('part 2')
            time.sleep(1)

            # send to new leader
            self._send_random_messages(producer, 10)

            broker.open()
            time.sleep(3)

            # count number of messages
            count = self._count_messages('test_switch_leader group %s' % i, topic)
            self.assertIn(count, range(20 * i, 22 * i + 1))

        producer.stop()

    def test_switch_leader_async(self):

        key, topic, partition = random_string(5), 'test_switch_leader_async', 0
        producer = SimpleProducer(self.client, topic, async=True)

        for i in range(1, 4):

            self._send_random_messages(producer, 10)

            # kil leader for partition 0
            broker = self._kill_leader(topic, partition)

            # expect failure, reload meta data
            producer.send_messages('part 1')
            producer.send_messages('part 2')
            time.sleep(1)

            # send to new leader
            self._send_random_messages(producer, 10)

            broker.open()
            time.sleep(3)

            # count number of messages
            count = self._count_messages('test_switch_leader_async group %s' % i, topic)
            self.assertIn(count, range(20 * i, 22 * i + 1))

        producer.stop()

    def _send_random_messages(self, producer, n):
        for j in range(n):
            resp = producer.send_messages(random_string(10))
            if len(resp) > 0:
                self.assertEquals(resp[0].error, 0)
        time.sleep(1) # give it some time

    def _kill_leader(self, topic, partition):
        leader = self.client.topics_to_brokers[TopicAndPartition(topic, partition)]
        broker = self.brokers[leader.nodeId]
        broker.close()
        time.sleep(1) # give it some time
        return broker

    def _count_messages(self, group, topic):
        client   = KafkaClient(self.brokers[0].host, self.brokers[0].port)
        consumer = SimpleConsumer(client, group, topic, auto_commit=False)
        all_messages = []
        for message in consumer:
            all_messages.append(message)
        consumer.stop()
        client.close()
        return len(all_messages)


def random_string(l):
    s = "".join(random.choice(string.letters) for i in xrange(l))
    return s

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
