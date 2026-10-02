import 'dart:async';

import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

/// STAP 2:
/// 'n Eenvoudige MQTT listener vir plaaslike toetsing.
///
/// Die broker-host word NIE hard-code na een rekenaar-IP nie.
/// Gee dit met:
///   flutter run --dart-define=MQTT_HOST=127.0.0.1
///
/// Vir 'n Android emulator kan die default 10.0.2.2 gebruik word.
class NoodgevalMqttService {
  NoodgevalMqttService._();

  static final NoodgevalMqttService instance = NoodgevalMqttService._();

  static const String host = String.fromEnvironment(
    'MQTT_HOST',
    defaultValue: '10.0.2.2',
  );

  static const int port = int.fromEnvironment(
    'MQTT_PORT',
    defaultValue: 1883,
  );

  MqttServerClient? _client;
  StreamSubscription<List<MqttReceivedMessage<MqttMessage?>>>? _subscription;
  String? _currentTopic;

  bool get isConnected =>
      _client?.connectionStatus?.state == MqttConnectionState.connected;

  String? get currentTopic => _currentTopic;

  Future<void> connect({
    required int kampusId,
    required void Function(String topic, String payload) onMessage,
  }) async {
    final topic = 'moon/noodgeval/kampus/$kampusId';

    // Indien ons reeds korrek gekoppel is, hoef ons nie weer te connect nie.
    if (isConnected && _currentTopic == topic) {
      return;
    }

    await disconnect();

    final clientId =
        'moon_flutter_${DateTime.now().millisecondsSinceEpoch.toString()}';

    final client = MqttServerClient.withPort(host, clientId, port)
      ..logging(on: false)
      ..keepAlivePeriod = 20
      ..autoReconnect = true
      ..resubscribeOnAutoReconnect = true
      ..secure = false
      ..connectionMessage = MqttConnectMessage()
          .withClientIdentifier(clientId)
          .startClean()
          .withWillQos(MqttQos.atLeastOnce);

    _client = client;

    try {
      await client.connect().timeout(const Duration(seconds: 8));
    } on TimeoutException {
      client.disconnect();
      throw Exception(
        'MQTT verbinding het uitgetel ($host:$port). '
        'Kontroleer dat Mosquitto loop en dat die foon die rekenaar kan bereik.',
      );
    } catch (e) {
      client.disconnect();
      throw Exception('Kon nie aan MQTT koppel by $host:$port nie: $e');
    }

    if (client.connectionStatus?.state != MqttConnectionState.connected) {
      final status = client.connectionStatus;
      client.disconnect();
      throw Exception(
        'MQTT verbinding geweier: ${status?.returnCode ?? status?.state}',
      );
    }

    _currentTopic = topic;
    client.subscribe(topic, MqttQos.atLeastOnce);

    final updates = client.updates;
    if (updates == null) {
      throw Exception('MQTT updates stream is nie beskikbaar nie.');
    }

    _subscription = updates.listen(
      (List<MqttReceivedMessage<MqttMessage?>> messages) {
        for (final message in messages) {
          final payloadMessage = message.payload;
          if (payloadMessage is! MqttPublishMessage) {
            continue;
          }

          final payload = MqttPublishPayload.bytesToStringAsString(
            payloadMessage.payload.message,
          );

          onMessage(message.topic, payload);
        }
      },
      onError: (Object error, StackTrace stackTrace) {
        // Vir Stap 2 log ons net die stream-fout.
        // Die foreground-service/reconnect UX kom in 'n latere stap.
        print('MQTT STREAM ERROR: $error');
      },
    );
  }

  Future<void> disconnect() async {
    await _subscription?.cancel();
    _subscription = null;

    final client = _client;
    _client = null;
    _currentTopic = null;

    if (client != null) {
      client.disconnect();
    }
  }
}
