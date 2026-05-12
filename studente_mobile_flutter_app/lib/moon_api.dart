import 'dart:convert';

import 'package:http/http.dart' as http;

/// Een rekord soos FastAPI `/lokasies` dit terugstuur (onder `data`).
class LokasieDto {
  final int id;
  final String naam;
  final String? beskrywing;
  final int? kampusId;

  LokasieDto({
    required this.id,
    required this.naam,
    this.beskrywing,
    this.kampusId,
  });

  factory LokasieDto.fromJson(Map<String, dynamic> json) {
    return LokasieDto(
      id: json['id'] as int,
      naam: json['naam'] as String,
      beskrywing: json['beskrywing'] as String?,
      kampusId: json['kampus_id'] as int?,
    );
  }
}

/// HTTP-koppel aan die FastAPI-backend (`main.py`).
///
/// Stel [bearerToken] ná werklike login (`POST /token`) sodat beskermde roetes werk.
/// Vir Android-emulator: gebruik gewoonlik `http://10.0.2.2:8000`.
/// Vir fisiese toestel: jou rekenaar se LAN-IP, bv. `http://192.168.1.10:8000`.
class MoonApi {
  MoonApi._();

  static String baseUrl = 'http://10.0.2.2:8000';

  /// JWT van `POST /token` (veld `access_token` binne `data`).
  static String? bearerToken;

  /// Haal alle klasse/lokasies uit die databasis (`GET /lokasies`).
  static Future<List<LokasieDto>> fetchLokasies() async {
    final uri = Uri.parse('$baseUrl/lokasies');
    final headers = <String, String>{
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    };

    final response = await http.get(uri, headers: headers);

    if (response.statusCode == 401 || response.statusCode == 403) {
      throw Exception(
        'Geen toegang tot /lokasies (HTTP ${response.statusCode}). '
        'Stel MoonApi.bearerToken na \'n geldige JWT (POST /token).',
      );
    }

    if (response.statusCode != 200) {
      throw Exception(
        'Bedienerfout HTTP ${response.statusCode}: ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception('Ongeldige JSON-antwoord');
    }

    if (decoded['sukses'] != true) {
      final fout = decoded['fout']?.toString() ?? 'Onbekende fout';
      throw Exception(fout);
    }

    final raw = decoded['data'];
    if (raw == null) return [];

    if (raw is! List) {
      throw Exception('Verwag \'data\' as lys');
    }

    return raw
        .map((e) => LokasieDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }
}
