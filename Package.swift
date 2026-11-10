// swift-tools-version: 5.9
//
// Root manifest so a SwiftPM consumer can depend on this repository by git URL
// and tag, like the npm and Python consumers do. It only points at the
// generated sources in gen/swift; the tests live in gen/swift's own package.

import PackageDescription

let package = Package(
    name: "NeedleProtocol",
    platforms: [.iOS(.v16), .macOS(.v13)],
    products: [
        .library(name: "NeedleProtocol", targets: ["NeedleProtocol"]),
    ],
    targets: [
        .target(name: "NeedleProtocol", path: "gen/swift/Sources/NeedleProtocol"),
    ]
)
