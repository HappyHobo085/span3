import 'dart:convert';

import 'package:http/http.dart' as http;

/// Een kampus soos FastAPI `/kampusse` dit terugstuur (onder `data`).
class KampusDto {
  final int? kampusId;
  final String naam;

  KampusDto({required this.kampusId, required this.naam});

  factory KampusDto.fromJson(Map<String, dynamic> json) {
    return KampusDto(
      kampusId: json['Kampus_ID'] as int?,
      naam: json['KAM_Naam'] as String,
    );
  }
}

/// Een rekord soos FastAPI `/lokasies` dit terugstuur (onder `data`).
class LokasieDto {
  final int? id;
  final String naam;
  final String? beskrywing;
  final int? kampusId;
  final String? nfcUid;

  LokasieDto({
    required this.id,
    required this.naam,
    this.beskrywing,
    this.kampusId,
    this.nfcUid,
  });

    factory LokasieDto.fromJson(Map<String, dynamic> json) {
    return LokasieDto(
      id: json['Lokasie_ID'] as int?,
      naam: json['LOK_Naam'] as String,
      beskrywing: json['LOK_Tipe'] as String?,
      kampusId: json['Kampus_ID'] as int?,
      nfcUid: json['NFC_UID'] as String?,
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

  static String baseUrl = "http://100.103.103.103:8000";

  /// JWT van `POST /token` (veld `access_token` binne `data`).
  static String? bearerToken;

  /// Haal alle kampusse (`GET /kampusse` — gewoonlik sonder JWT).
  static Future<List<KampusDto>> fetchKampusse() async {
    final uri = Uri.parse('$baseUrl/kampusse');
    final headers = <String, String>{
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    };

    final response = await http.get(uri, headers: headers);

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
        .map((e) => KampusDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

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
