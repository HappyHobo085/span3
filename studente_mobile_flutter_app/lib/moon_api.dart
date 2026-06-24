import 'dart:convert';
import 'package:http/http.dart' as http;

/// =========================
/// Kampus DTO
/// =========================

class KampusDto {
  final int? kampusId;
  final String naam;

  KampusDto({
    required this.kampusId,
    required this.naam,
  });

  factory KampusDto.fromJson(Map<String, dynamic> json) {
    return KampusDto(
      kampusId: json['Kampus_ID'] as int?,
      naam: json['KAM_Naam'] as String,
    );
  }
}

/// =========================
/// Lokasie DTO
/// =========================

class LokasieDto {
  final int id;
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
      id: json['Lokasie_ID'] as int,
      naam: json['LOK_Naam'] as String,
      beskrywing: json['LOK_Tipe'] as String?,
      kampusId: json['Kampus_ID'] as int?,
      nfcUid: json['NFC_UID'] as String?,
    );
  }
}

/// =========================
/// Moon API
/// =========================

class MoonApi {
  MoonApi._();

  /// Verander na jou backend IP
  static String baseUrl = "http://happyhobo-pc.tail251156.ts.net:8000";

  /// JWT token indien benodig
  static String? bearerToken;
  static Future<Map<String, dynamic>> login({
    required String email,
    required String password,
    }) async {
    final uri = Uri.parse('$baseUrl/token');

    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
      },
      body: {
        'grant_type': 'password',
        'username': email,
        'password': password,
        'scope': '',
        'client_id': '',
        'client_secret': '',
      },
    );

  final decoded = jsonDecode(response.body);

  if (response.statusCode != 200 || decoded['sukses'] != true) {
    throw Exception(
      decoded['fout'] ?? decoded['detail'] ?? 'Login het misluk',
    );
  }

  final token = decoded['data']['access_token'] as String;
  bearerToken = token;

  return Map<String, dynamic>.from(decoded['data']);
}
  /// -------------------------
  /// Kampusse
  /// -------------------------

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

    if (decoded['sukses'] != true) {
      throw Exception(
        decoded['fout']?.toString() ?? 'Kon nie kampusse laai nie',
      );
    }

    final raw = decoded['data'];

    if (raw == null) return [];

    return (raw as List)
        .map((e) => KampusDto.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  /// -------------------------
  /// Lokasies
  /// -------------------------
  static Future<Map<String, dynamic>> studentScanKlas({
    required String nfcUid,
    required String rigting,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/student/scan-klas'),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer ${bearerToken!}',
      },
      body: jsonEncode({
        'nfc_uid': nfcUid,
        'rigting': rigting,
      }),
    );

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 ||
        decoded['sukses'] != true) {
      throw Exception(
        decoded['detail'] ??
            decoded['fout'] ??
            'Scan het misluk',
      );
    }

    return Map<String, dynamic>.from(decoded['data']);
  }


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
        'Geen toegang tot lokasies nie. Login asseblief weer.',
      );
    }

    if (response.statusCode != 200) {
      throw Exception(
        'Bedienerfout HTTP ${response.statusCode}: ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded['sukses'] != true) {
      throw Exception(
        decoded['fout']?.toString() ?? 'Kon nie lokasies laai nie',
      );
    }

    final raw = decoded['data'];

    if (raw == null) return [];

    return (raw as List)
        .map((e) => LokasieDto.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  /// -------------------------
  /// Wagte Student Scan
  /// -------------------------

  static Future<Map<String, dynamic>> wagteStudentScan({
    required String studentNomOrId,
    required int lokasieId,
    required String rigting,
    required String metode,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/wagte/student/scan'),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (bearerToken != null && bearerToken!.trim().isNotEmpty)
          'Authorization': 'Bearer ${bearerToken!.trim()}',
      },
      body: jsonEncode({
        'student_nom_or_id': studentNomOrId,
        'lokasie_id': lokasieId,
        'rigting': rigting,
        'metode': metode,
      }),
    );

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        decoded['detail'] ??
            decoded['fout'] ??
            'Student skandering het misluk',
      );
    }

    if (decoded['sukses'] != true) {
      throw Exception(
        decoded['fout'] ?? 'Student skandering het misluk',
      );
    }

    return Map<String, dynamic>.from(decoded['data']);
  }
}



