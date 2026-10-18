# Mobile toolchain compatibility

## Expo and native packages

The mobile application uses the stable Expo SDK 58 release, React Native 0.88, and React 19.3. Expo packages, native screen and safe-area packages, Jest, and React types are aligned through `npx expo install --fix`. Dependabot groups this SDK stack into one proposal to reduce incompatible partial updates. Grouping does not guarantee upstream compatibility: keep the online `npx expo install --check` gate enabled when updating this set.

SDK 58 was released on October 15, 2026. Follow the [SDK 58 migration notes](https://expo.dev/changelog/sdk-58) when changing native configuration. Existing development builds must be rebuilt after upgrading the SDK. Store versions of Expo Go may lag the SDK release; use a development build while that rollout completes.

## TypeScript compiler and API compatibility

`npm run typecheck` runs TypeScript 7 explicitly. The `typescript-7` npm alias keeps the new compiler independent of tools that require the JavaScript compiler API. ESLint and other API consumers resolve the supported TypeScript 6 package. Both are locked and validated; no peer dependency checks are bypassed.

Do not replace the API package with TypeScript 7 until its consumers support that API. Update both compiler paths through the existing CI checks.

## Component tests

React Native Testing Library 14 uses `test-renderer`. Rendering and fire events are asynchronous: await every `render`, shared rendering helper, and `fireEvent` call before querying or asserting the resulting interface. The complete behavior suite and the existing coverage thresholds remain required. Jest retains the JS/TS test filename patterns used before Jest 30. Node security regression files use their own runner through `npm run test:security`, which is a separate required CI step.

CI configuration, project-authored diagnostics, and contribution standards use English.
