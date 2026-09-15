import 'dart:convert';

import 'package:flutter/material.dart';

import 'package:flutter/services.dart';

import 'package:google_fonts/google_fonts.dart';

import 'app_shared.dart';

import 'student.dart';

import 'personeel.dart';

import 'opsigter.dart';

import 'sekuriteitswag.dart';

import 'admin.dart';

import 'moon_api.dart';

final GlobalKey<ScaffoldMessengerState> rootScaffoldMessengerKey =

    GlobalKey<ScaffoldMessengerState>();

const MethodChannel _noodgevalServiceChannel =

    MethodChannel('moon/noodgeval_service');

const String _mqttHost = String.fromEnvironment(
  'MQTT_HOST',
  defaultValue: 'wss://mqtt-production-bea8.up.railway.app/mqtt',
);

const int _mqttPort = int.fromEnvironment(
  'MQTT_PORT',
  defaultValue: 443,
);

const String _mqttUsername = String.fromEnvironment(
  'MQTT_USERNAME',
  defaultValue: 'moon_mobile',
);

const String _mqttPassword = String.fromEnvironment(
  'MQTT_PASSWORD',
  defaultValue: '',
);

Future<void> _startNativeNoodgevalService({required String bearerToken}) async {

  try {
    if (_mqttUsername.isNotEmpty && _mqttPassword.isEmpty) {
      throw Exception(
        'MQTT_PASSWORD ontbreek. Begin die app met '
        '--dart-define=MQTT_PASSWORD=<jou mobile MQTT wagwoord>.',
      );
    }

    final started = await _noodgevalServiceChannel.invokeMethod<bool>(

      'start',

      <String, dynamic>{

        'host': _mqttHost,

        'port': _mqttPort,

        'mqttUsername': _mqttUsername,

        'mqttPassword': _mqttPassword,

        // Kampus 1 bly vir nou die plaaslike toetskampus.

        // Ons koppel later die regte kampus per gebruiker.

        'kampusId': 1,

        // Die native service moet self kan rapporteer wanneer Flutter

        // uit Recent Apps wegge-swipe is.

        'apiBaseUrl': MoonApi.baseUrl,

        'bearerToken': bearerToken,

      },

    );

    debugPrint(

      'NATIVE NOODGEVAL SERVICE: '

      'started=$started host=$_mqttHost port=$_mqttPort '
      'user=$_mqttUsername kampus=1',

    );

  } catch (e) {

    debugPrint('NATIVE NOODGEVAL SERVICE ERROR: $e');

    rootScaffoldMessengerKey.currentState?.showSnackBar(

      SnackBar(

        duration: const Duration(seconds: 8),

        backgroundColor: Colors.orange.shade800,

        content: Text(

          'Noodgevaldiens kon nie begin nie: $e',

          style: const TextStyle(color: Colors.white),

        ),

      ),

    );

  }

}

void main() {

  WidgetsFlutterBinding.ensureInitialized();

  runApp(const MyApp());

}

Map<String, dynamic> _decodeJwtPayload(String token) {

  final parts = token.split('.');

  if (parts.length != 3) {

    throw Exception('Ongeldige token');

  }

  final payload = base64Url.normalize(parts[1]);

  final decoded = utf8.decode(base64Url.decode(payload));

  final json = jsonDecode(decoded);

  if (json is! Map<String, dynamic>) {

    throw Exception('Ongeldige token: ongeldige lading');

  }

  return json;

}

/// Kies die rol vir roetering uit die JWT se `roles`-lys volgens prioriteit.

/// Onbekende rolle word geïgnoreer; val terug op `rol_naam` indien nodig.

String _pickRole(Map<String, dynamic> payload) {

  const priority = [

    'Administrateur',

    'Kampus_Opsigter',

    'Sekuriteit_Wag',

    'Personeel',

    'Student',

  ];

  final rolesRaw = payload['roles'];

  final roles = (rolesRaw is List && rolesRaw.isNotEmpty)

      ? rolesRaw.map((r) => r.toString()).toList()

      : <String>[payload['rol_naam']?.toString() ?? ''];

  for (final rol in priority) {

    if (roles.contains(rol)) {

      return rol;

    }

  }

  throw Exception('Onbekende rol: ${roles.join(', ')}');

}

class MyApp extends StatelessWidget {

  const MyApp({super.key});

  @override

  Widget build(BuildContext context) {

    return MaterialApp(

      scaffoldMessengerKey: rootScaffoldMessengerKey,

      title: 'MOON — Kampus Bestuur',

      debugShowCheckedModeBanner: false,

      theme: ThemeData(

        useMaterial3: true,

        scaffoldBackgroundColor: kBg,

        colorScheme: ColorScheme.dark(

          primary: kAccent,

          secondary: kAccent2,

          surface: kSurface1,

        ),

        textTheme: GoogleFonts.interTextTheme(

          ThemeData.dark().textTheme,

        ),

      ),

      home: const LoginPage(),

    );

  }

}

class LoginPage extends StatefulWidget {

  const LoginPage({super.key});

  @override

  State<LoginPage> createState() => _LoginPageState();

}

class _LoginPageState extends State<LoginPage> {

  final TextEditingController _usernameController = TextEditingController();

  final TextEditingController _passwordController = TextEditingController();

  bool _isLoading = false;

  @override

  void dispose() {

    _usernameController.dispose();

    _passwordController.dispose();

    super.dispose();

  }

  Future<void> _handleLogin() async {

    final username = _usernameController.text.trim();

    final password = _passwordController.text.trim();

    if (username.isEmpty || password.isEmpty) {

      ScaffoldMessenger.of(context).showSnackBar(

        const SnackBar(

          backgroundColor: Colors.red,

          content: Text(

            'Voer asseblief gebruikersnaam en wagwoord in.',

            style: TextStyle(color: Colors.white),

          ),

        ),

      );

      return;

    }

    setState(() => _isLoading = true);

    try {

      final loginData = await MoonApi.login(

        email: username,

        password: password,

      );

      final rawToken = loginData['access_token'];

      if (rawToken is! String || rawToken.isEmpty) {

        throw Exception(

          'Aanmelding het misluk: geen toegangstoken ontvang nie.',

        );

      }

      final token = rawToken;

      final payload = _decodeJwtPayload(token);

      final rolNaam = _pickRole(payload);

      Widget nextPage;

      switch (rolNaam) {

        case 'Administrateur':

          nextPage = const AdminHomePage();

          break;

        case 'Personeel':

          nextPage = const PersoneelHomePage();

          break;

        case 'Kampus_Opsigter':

          nextPage = const OpsigterHomePage();

          break;

        case 'Sekuriteit_Wag':

          nextPage = const SekuriteitswagHomePage();

          break;

        case 'Student':

          nextPage = const HomePage();

          break;

        default:

          throw Exception('Onbekende rol: $rolNaam');

      }

      await MoonApi.getMyProfile();

      // Begin die native Android foreground service.

      // MQTT loop dan buite die Flutter UI en bly aktief wanneer die app

      // uit Recent Apps wegge-swipe word.

      await _startNativeNoodgevalService(bearerToken: token);

      if (!mounted) return;

      Navigator.pushReplacement(

        context,

        MaterialPageRoute(builder: (_) => nextPage),

      );

    } catch (e) {

      debugPrint('LOGIN ERROR: $e');

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(

        SnackBar(

          backgroundColor: Colors.red,

          content: Text(

            'Login fout: $e',

            style: const TextStyle(color: Colors.white),

          ),

        ),

      );

    } finally {

      if (mounted) {

        setState(() => _isLoading = false);

      }

    }

  }

  @override

  Widget build(BuildContext context) {

    return Scaffold(

      backgroundColor: kBg,

      body: SafeArea(

        child: Center(

          child: SingleChildScrollView(

            padding: const EdgeInsets.all(24),

            child: ConstrainedBox(

              constraints: const BoxConstraints(maxWidth: 360),

              child: Column(

                mainAxisSize: MainAxisSize.min,

                children: [

                  GlassCard(

                    padding: const EdgeInsets.symmetric(

                      vertical: 28,

                      horizontal: 24,

                    ),

                    child: Column(

                      children: [

                        ShaderMask(

                          shaderCallback: (bounds) =>

                              kGradient.createShader(bounds),

                          child: Text(

                            'MOON',

                            style: GoogleFonts.inter(

                              color: Colors.white,

                              fontSize: 28,

                              fontWeight: FontWeight.w800,

                              letterSpacing: 4,

                            ),

                          ),

                        ),

                        const SizedBox(height: 4),

                        Text(

                          'KAMPUS BESTUUR STELSEL',

                          style: GoogleFonts.inter(

                            color: kTextMuted,

                            fontSize: 9,

                            fontWeight: FontWeight.w600,

                            letterSpacing: 2,

                          ),

                        ),

                      ],

                    ),

                  ),

                  const SizedBox(height: 24),

                  GlassInput(

                    controller: _usernameController,

                    hintText: 'Gebruikers e-pos / Studentenommer',

                    keyboardType: TextInputType.text,

                  ),

                  const SizedBox(height: 12),

                  GlassInput(

                    controller: _passwordController,

                    hintText: 'Wagwoord',

                    obscureText: true,

                    prefixIcon: const Icon(

                      Icons.lock_outline,

                      color: kTextMuted,

                      size: 18,

                    ),

                  ),

                  const SizedBox(height: 24),

                  GradientActionButton(

                    label: _isLoading ? 'Teken in...' : 'Teken In',

                    onTap: _isLoading

                        ? () {}

                        : () async {

                            await _handleLogin();

                          },

                    width: double.infinity,

                    height: 48,

                  ),

                ],

              ),

            ),

          ),

        ),

      ),

    );

  }

}