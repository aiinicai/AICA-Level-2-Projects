import 'dart:math';

import 'package:family_vault/src/domain/password_generator.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for the generator.
///
/// The properties that matter are that it draws from a secure source, that it
/// honours what the user asked for, and that "include symbols" really means at
/// least one symbol appears — because sites reject passwords that do not, and
/// a generator that merely makes them likely will occasionally produce one the
/// user cannot use.
void main() {
  final PasswordGenerator generator = PasswordGenerator();

  group('length', () {
    test('produces exactly the requested length', () {
      for (final int length in <int>[8, 12, 20, 32, 64, 128]) {
        expect(
          generator.password(PasswordRecipe(length: length)).length,
          length,
          reason: 'failed at length $length',
        );
      }
    });

    test('refuses a length below the minimum', () {
      expect(
        () => generator.password(
          const PasswordRecipe(length: PasswordRecipe.minLength - 1),
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('refuses a length above the maximum', () {
      expect(
        () => generator.password(
          const PasswordRecipe(length: PasswordRecipe.maxLength + 1),
        ),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  group('character sets are honoured, not merely likely', () {
    // Repeated because the guarantee is about every password, not the average
    // one. A generator that only usually includes a digit will eventually hand
    // the user a password the site rejects.
    const int attempts = 200;

    test('digits only', () {
      for (int i = 0; i < attempts; i++) {
        final String password = generator.password(
          const PasswordRecipe(
            length: 10,
            uppercase: false,
            lowercase: false,
            symbols: false,
          ),
        );
        expect(RegExp(r'^[0-9]+$').hasMatch(password), isTrue);
      }
    });

    test('lower case only', () {
      for (int i = 0; i < attempts; i++) {
        final String password = generator.password(
          const PasswordRecipe(
            length: 10,
            uppercase: false,
            digits: false,
            symbols: false,
          ),
        );
        expect(RegExp(r'^[a-z]+$').hasMatch(password), isTrue);
      }
    });

    test('every selected set appears at least once, every time', () {
      for (int i = 0; i < attempts; i++) {
        final String password = generator.password(
          const PasswordRecipe(length: 12),
        );
        expect(password.contains(RegExp('[a-z]')), isTrue, reason: password);
        expect(password.contains(RegExp('[A-Z]')), isTrue, reason: password);
        expect(password.contains(RegExp('[0-9]')), isTrue, reason: password);
        expect(
          password.contains(RegExp(r'[^A-Za-z0-9]')),
          isTrue,
          reason: password,
        );
      }
    });

    test('refuses a recipe with no character sets at all', () {
      expect(
        () => generator.password(
          const PasswordRecipe(
            uppercase: false,
            lowercase: false,
            digits: false,
            symbols: false,
          ),
        ),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  group('ambiguous characters', () {
    test('are left out when asked', () {
      for (int i = 0; i < 100; i++) {
        final String password = generator.password(
          const PasswordRecipe(length: 40, avoidAmbiguous: true),
        );
        for (final String character in PasswordRecipe.ambiguous.split('')) {
          expect(
            password.contains(character),
            isFalse,
            reason: 'found "$character" in $password',
          );
        }
      }
    });
  });

  group('randomness', () {
    test('does not repeat itself', () {
      final Set<String> seen = <String>{};
      for (int i = 0; i < 200; i++) {
        seen.add(generator.password(const PasswordRecipe(length: 16)));
      }
      expect(seen.length, 200);
    });

    test('the guaranteed characters are not always in the same place', () {
      // If the required characters were simply placed at the front, the first
      // character would always come from the same set. This checks the shuffle
      // actually moved them.
      final Set<String> firstCharacters = <String>{};
      for (int i = 0; i < 200; i++) {
        firstCharacters.add(
          generator.password(const PasswordRecipe(length: 12))[0],
        );
      }
      final bool sawLower = firstCharacters.any(
        (String c) => RegExp('[a-z]').hasMatch(c),
      );
      final bool sawSymbol = firstCharacters.any(
        (String c) => RegExp(r'[^A-Za-z0-9]').hasMatch(c),
      );
      expect(sawLower && sawSymbol, isTrue);
    });

    test('is reproducible only when given a seeded source, for tests', () {
      final PasswordGenerator a = PasswordGenerator.withRandom(Random(42));
      final PasswordGenerator b = PasswordGenerator.withRandom(Random(42));
      expect(
        a.password(const PasswordRecipe(length: 20)),
        b.password(const PasswordRecipe(length: 20)),
      );
    });
  });

  group('passphrases', () {
    test('have the requested number of words', () {
      for (final int words in <int>[3, 4, 5, 8, 12]) {
        final String phrase = generator.passphrase(
          PassphraseRecipe(wordCount: words),
        );
        expect(phrase.split('-').length, words);
      }
    });

    test(
      'clamp a request below the minimum rather than producing one word',
      () {
        final String phrase = generator.passphrase(
          const PassphraseRecipe(wordCount: 1),
        );
        expect(phrase.split('-').length, PassphraseRecipe.minWords);
      },
    );

    test('use the chosen separator', () {
      final String phrase = generator.passphrase(
        const PassphraseRecipe(wordCount: 4, separator: '.'),
      );
      expect(phrase.split('.').length, 4);
    });

    test('capitalise each word when asked', () {
      final String phrase = generator.passphrase(
        const PassphraseRecipe(wordCount: 4, capitalise: true),
      );
      for (final String word in phrase.split('-')) {
        expect(word[0], word[0].toUpperCase());
      }
    });

    test('append a number when asked', () {
      final String phrase = generator.passphrase(
        const PassphraseRecipe(wordCount: 4, includeNumber: true),
      );
      final List<String> parts = phrase.split('-');
      expect(parts.length, 5);
      expect(int.tryParse(parts.last), isNotNull);
    });

    test('do not repeat themselves', () {
      final Set<String> seen = <String>{};
      for (int i = 0; i < 100; i++) {
        seen.add(generator.passphrase(const PassphraseRecipe()));
      }
      expect(seen.length, greaterThan(95));
    });
  });

  group('the word list', () {
    // The documented entropy claim depends on this being exactly 256, so it
    // is asserted rather than left as a comment that could drift.
    test('is exactly 256 words, so each word is exactly 8 bits', () {
      expect(PasswordGenerator.wordList.length, 256);
    });

    test('has no duplicates, which would skew the odds', () {
      expect(
        PasswordGenerator.wordList.toSet().length,
        PasswordGenerator.wordList.length,
      );
    });

    test('is all lower-case letters, so separators stay unambiguous', () {
      for (final String word in PasswordGenerator.wordList) {
        expect(
          RegExp(r'^[a-z]+$').hasMatch(word),
          isTrue,
          reason: '"$word" is not plain lower-case letters',
        );
      }
    });

    test('has no words so short they add little', () {
      for (final String word in PasswordGenerator.wordList) {
        expect(word.length, greaterThanOrEqualTo(3), reason: word);
      }
    });
  });

  group('usernames', () {
    test('look like two words and a number', () {
      final String username = generator.username();
      expect(
        RegExp(r'^[a-z]+\.[a-z]+[0-9]{1,3}$').hasMatch(username),
        isTrue,
        reason: username,
      );
    });

    test('vary', () {
      final Set<String> seen = <String>{};
      for (int i = 0; i < 100; i++) {
        seen.add(generator.username());
      }
      expect(seen.length, greaterThan(90));
    });
  });
}
