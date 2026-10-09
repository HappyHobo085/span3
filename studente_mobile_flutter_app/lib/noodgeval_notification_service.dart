import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NoodgevalNotificationService {
  NoodgevalNotificationService._();

  static final NoodgevalNotificationService instance =
      NoodgevalNotificationService._();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  bool _initialized = false;

  Future<void> initialize() async {
    if (_initialized) return;

    const androidSettings = AndroidInitializationSettings('ic_stat_moon');
    const settings = InitializationSettings(android: androidSettings);

    await _plugin.initialize(settings);

    final android = _plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();

    // Android 13+ vra runtime toestemming vir gewone notifications.
    await android?.requestNotificationsPermission();

    _initialized = true;
  }

  Future<void> showMqttTest({
    required String topic,
    required String payload,
  }) async {
    if (!_initialized) {
      await initialize();
    }

    const androidDetails = AndroidNotificationDetails(
      'moon_noodgeval_test',
      'MOON-noodgevaltoets',
      channelDescription: 'MQTT-noodgevaltoetsboodskappe',
      importance: Importance.high,
      priority: Priority.high,
      playSound: false,
      enableVibration: false,
      ongoing: false,
      autoCancel: true,
    );

    const details = NotificationDetails(android: androidDetails);

    await _plugin.show(
      3001,
      '🚨 MOON MQTT TOETS ONTVANG',
      payload,
      details,
      payload: topic,
    );
  }
}
