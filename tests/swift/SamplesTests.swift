import Foundation
import XCTest

@testable import NeedleProtocol

/// Runs the tracker entries of `tests/samples.json` -- the same frames the
/// TypeScript (zod) and Python (pydantic) suites validate -- through the generated
/// Swift types. Every `valid` frame must decode; every `invalid` one must not.
///
/// The file is found relative to this source file, which tools/gen.sh copies to
/// `gen/swift/Tests/NeedleProtocolTests/`: five components up is the repository root.
final class SamplesTests: XCTestCase {
    private struct Entry: Decodable {
        let contract: String
        let name: String
        let frame: JSONValue
    }

    private struct Samples: Decodable {
        let valid: [Entry]
        let invalid: [Entry]
    }

    /// Just enough JSON to hand a sample frame back to `JSONDecoder` as bytes.
    private enum JSONValue: Codable {
        case null, bool(Bool), number(Double), string(String), array([JSONValue]), object([String: JSONValue])

        init(from decoder: Decoder) throws {
            let c = try decoder.singleValueContainer()
            if c.decodeNil() { self = .null }
            else if let v = try? c.decode(Bool.self) { self = .bool(v) }
            else if let v = try? c.decode(Double.self) { self = .number(v) }
            else if let v = try? c.decode(String.self) { self = .string(v) }
            else if let v = try? c.decode([JSONValue].self) { self = .array(v) }
            else { self = .object(try c.decode([String: JSONValue].self)) }
        }

        func encode(to encoder: Encoder) throws {
            var c = encoder.singleValueContainer()
            switch self {
            case .null: try c.encodeNil()
            case .bool(let v): try c.encode(v)
            case .number(let v): try c.encode(v)
            case .string(let v): try c.encode(v)
            case .array(let v): try c.encode(v)
            case .object(let v): try c.encode(v)
            }
        }
    }

    private static let trackerContracts = ["TrackerHello", "TrackerFrameStatus", "TrackerFrameNeedle"]

    private func loadSamples() throws -> Samples {
        var url = URL(fileURLWithPath: #filePath)
        for _ in 0..<5 { url.deleteLastPathComponent() }
        let data = try Data(contentsOf: url.appendingPathComponent("tests/samples.json"))
        return try JSONDecoder().decode(Samples.self, from: data)
    }

    /// The raw bytes of a sample frame, re-serialised from the parsed JSON.
    ///
    /// A fractional `frame_id: 1.5` stays fractional, so `Int` decoding still
    /// refuses it; whole numbers are re-emitted as whole numbers.
    private func bytes(_ entry: Entry) throws -> Data {
        try JSONEncoder().encode(entry.frame)
    }

    private func decode(_ contract: String, _ data: Data) throws {
        let decoder = JSONDecoder()
        switch contract {
        case "TrackerHello": _ = try decoder.decode(TrackerHello.self, from: data)
        case "TrackerFrameStatus": _ = try decoder.decode(TrackerFrameStatus.self, from: data)
        case "TrackerFrameNeedle": _ = try decoder.decode(TrackerFrameNeedle.self, from: data)
        default: XCTFail("no Swift type for contract \(contract)")
        }
    }

    func testEveryValidTrackerSampleDecodes() throws {
        let entries = try loadSamples().valid.filter { Self.trackerContracts.contains($0.contract) }
        // Each contract must be represented, so an emptied or renamed sample set fails
        // here instead of passing a loop that runs zero times. Adding a sample needs
        // no change in this file.
        for contract in Self.trackerContracts {
            XCTAssertTrue(entries.contains { $0.contract == contract }, "no valid sample for \(contract)")
        }
        for entry in entries {
            XCTAssertNoThrow(try decode(entry.contract, try bytes(entry)), entry.name)
        }
    }

    func testEveryInvalidTrackerSampleIsRejected() throws {
        let entries = try loadSamples().invalid.filter { Self.trackerContracts.contains($0.contract) }
        XCTAssertFalse(entries.isEmpty, "no invalid tracker samples found")
        for entry in entries {
            XCTAssertThrowsError(try decode(entry.contract, try bytes(entry)), entry.name)
        }
    }

    private func sample(_ name: String) throws -> Data {
        let entry = try XCTUnwrap(try loadSamples().valid.first { $0.name == name }, name)
        return try bytes(entry)
    }

    func testDetectedNeedleFrame() throws {
        let frame = try JSONDecoder().decode(TrackerFrameNeedle.self, from: sample("tracker-frame-needle-detected"))
        XCTAssertEqual(frame.tipX, 12.5)
        XCTAssertEqual(frame.tipY, 30.25)
        XCTAssertEqual(frame.tipZ, -48.0)
        XCTAssertEqual(frame.entryX, 10.0)
        XCTAssertEqual(frame.source, .detected)
        XCTAssertEqual(frame.confLo, 0.91)
        XCTAssertEqual(frame.confHi, 0.88)
        XCTAssertEqual(frame.skinEntryX, 10.8)
        XCTAssertEqual(frame.frameId, 4821)
        XCTAssertEqual(frame.entryToTipMm, 38.4)
        XCTAssertEqual(frame.surfaceToTipMm, 28.1)
    }

    func testPredictedFrameHasNilConfidences() throws {
        let frame = try JSONDecoder().decode(TrackerFrameNeedle.self, from: sample("tracker-frame-needle-predicted"))
        XCTAssertEqual(frame.source, .predicted)
        XCTAssertNil(frame.confLo)
        XCTAssertNil(frame.confHi)
        XCTAssertEqual(frame.tipX, 12.5)
        XCTAssertEqual(frame.frameId, 4822)
    }

    func testNoSkinCrossingHasNilSkinEntryAndSurfaceLength() throws {
        let frame = try JSONDecoder().decode(TrackerFrameNeedle.self, from: sample("tracker-frame-needle-no-skin-crossing"))
        XCTAssertNil(frame.skinEntryX)
        XCTAssertNil(frame.skinEntryY)
        XCTAssertNil(frame.skinEntryZ)
        XCTAssertNil(frame.surfaceToTipMm)
        XCTAssertEqual(frame.entryToTipMm, 38.4)
    }

    func testUnknownKeysAreIgnored() throws {
        let frame = try JSONDecoder().decode(TrackerFrameNeedle.self, from: sample("tracker-frame-needle-additive-field"))
        XCTAssertEqual(frame.tipZ, -48.0)
        let hello = try JSONDecoder().decode(TrackerHello.self, from: sample("tracker-hello-additive-field"))
        XCTAssertEqual(hello.protocolVersion, 2)
    }

    func testHelloFields() throws {
        let hello = try JSONDecoder().decode(TrackerHello.self, from: sample("tracker-hello-v2"))
        XCTAssertEqual(hello.protocolVersion, 2)
        XCTAssertEqual(hello.serverBind, "0.0.0.0:8765")
        XCTAssertEqual(hello.clientAddr, "10.0.0.42")
        // `server_bind` and `client_addr` are not in `required`.
        let bare = try JSONDecoder().decode(TrackerHello.self, from: Data(#"{"type":"hello","protocol_version":1}"#.utf8))
        XCTAssertNil(bare.serverBind)
        XCTAssertNil(bare.clientAddr)
    }

    func testStatusFields() throws {
        let status = try JSONDecoder().decode(TrackerFrameStatus.self, from: sample("tracker-frame-status-degraded"))
        XCTAssertEqual(status.health, .degraded)
        XCTAssertEqual(status.issues, [.cameraLoMissing])
        XCTAssertFalse(status.needlePresent)
    }

    func testNullableRequiredKeyMustBePresent() {
        // A v1 rig has no conf_lo at all; absence is not the same as null.
        let v1 = #"""
        {"tipX":1,"tipY":2,"tipZ":3,"entryX":1,"entryY":2,"entryZ":3,"timestamp":1,"source":"detected",
         "conf_hi":0.5,"lastDetectionTimestamp":null,"skin_entry_x":null,"skin_entry_y":null,
         "skin_entry_z":null,"frame_id":1,"surface_to_tip_mm":null,"entry_to_tip_mm":1}
        """#
        XCTAssertThrowsError(try JSONDecoder().decode(TrackerFrameNeedle.self, from: Data(v1.utf8)))
    }

    func testEncodeRoundTripKeepsWireNamesAndExplicitNulls() throws {
        let frame = try JSONDecoder().decode(TrackerFrameNeedle.self, from: sample("tracker-frame-needle-predicted"))
        let encoded = try JSONEncoder().encode(frame)
        let object = try XCTUnwrap(try JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        XCTAssertEqual(object["tipX"] as? Double, 12.5)
        XCTAssertTrue(object["conf_lo"] is NSNull, "a required nullable field is written as null, not omitted")
        XCTAssertNotNil(object["skin_entry_x"])
        XCTAssertEqual(try JSONDecoder().decode(TrackerFrameNeedle.self, from: encoded), frame)
    }

    func testSupportedProtocolVersions() {
        XCTAssertEqual(NeedleProtocolConstants.trackerSupportedProtocolVersions, [1, 2])
    }
}
