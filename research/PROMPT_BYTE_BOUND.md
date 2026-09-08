# Conditional plain-text prompt byte bound — 2026-09-08

For the current literal prompts and standard CPython 3.11 binary64 short `repr`, the conservative bound is **108,739 ASCII bytes for an initial proposal request** and **108,835 bytes including the longest correction suffix**, allowing the protocol's 200-row boundary. The current renderer actually accepts at most 190 rows; its corresponding bounds are **103,449** and **103,545** bytes.

These count the sum of the system-message text and user-message text only. They are **not token ceilings, HTTP/JSON body ceilings, provider-rendered context ceilings, or bills**. No provider model/token-count endpoint, study objective, or optimization was called. No library was installed.

## Why 24 bytes per finite float is defensible

The check used CPython 3.11.15, `sys.float_repr_style == 'short'`, radix 2, 53-bit mantissa and ordinary IEEE-754 binary64 limits. The renderer explicitly converts accepted history values and coordinates to built-in `float` before applying `repr`; NumPy scalar formatting therefore does not control these strings.

The derivation is conditional on the standard CPython short-repr implementation and correct binary64 arithmetic, rather than a formal verification of the installed executable:

1. A finite binary64 value has a round-trip decimal representation with at most 17 significant decimal digits. One way to see sufficiency is to round the value to 17 significant decimal digits: relative error is at most `5e-17`, which is strictly smaller than `2**-54`, the conservative relative distance from a nonzero binary64 value to a nearest-rounding boundary. Subnormals have no tighter relative requirement. The shortest round-trip representation therefore needs no more than 17 significant digits. Zero and signed zero are separate, shorter cases.
2. CPython's `repr` mode calls the short conversion mode (`mode = 0`), whose source contract is to return the shortest string that rounds back to the input. Its repr formatter chooses scientific notation when the digit string's decimal-point position is at most -4 or greater than 16.
3. In scientific form, there are at most 17 significand digits, one decimal point, one leading minus, one `e`, one exponent sign and three exponent digits. The nonzero finite binary64 exponent range needed in this spelling is -324 through +308. Sum: `17 + 1 + 1 + 1 + 1 + 3 = 24` ASCII bytes. Omitting a decimal point in shorter cases only decreases length.
4. In fixed form, the decimal-point position is from -3 through 16. At the small end, `0.` plus three leading fractional zeros plus 17 significant digits plus a minus occupies at most `2 + 3 + 17 + 1 = 23` bytes. Other fixed cases, including appended `.0` for an integer, are no longer. `0.0` and `-0.0` have lengths 3 and 4.

Thus 24 is conservative for **all** finite built-in binary64 values and consequently for the much smaller mapped coordinate and objective domains. It is attainable for a legal coordinate, for example `-2.2250738585072014e-308`, which has length 24. Objective values are nonnegative apart from signed zero, so using 24 for them is deliberately loose.

Source inspection matched the `v3.11.15` tag. The matching version string is not a source-to-binary reproducibility proof:

- [CPython pystrtod.c](https://github.com/python/cpython/blob/v3.11.15/Python/pystrtod.c): repr formatting switch near line 1131, scientific threshold near 1137, exponent formatting near 1242, repr-to-mode-0 mapping near 1303. Retrieved bytes SHA-256 `44f25d7cad020289d271cb3ad920536d6fc168ae7d73a085989489ca362d3113`.
- [CPython dtoa.c](https://github.com/python/cpython/blob/v3.11.15/Python/dtoa.c): short-mode contract near line 2258. Retrieved bytes SHA-256 `54e376bda73ffee5972fc19dc0ad15e8928e7d078ca62e39cb3c5365015ceab4`.

Only public source text was fetched for this inspection; no source was executed or installed.

## Exact overhead and arithmetic

Current checked files are entirely ASCII, including their trailing LF:

| Component | Bytes |
|---|---:|
| `system_v0.3.txt` | 1,258 |
| `user_template_v0.3.txt` including placeholders | 1,704 |
| `{history_table}` | 15 |
| `{best_I}` | 8 |
| `{best_index}` | 12 |
| `{remaining_after}` | 17 |
| User text after removing the four single-occurrence placeholders | 1,652 |
| Fixed system + fixed user | 2,910 |
| Conservative scalar replacements: best_I 24, best_index 3, remaining_after 3 | 30 |
| Combined overhead excluding history | **2,940** |

Each history row contains 22 fields: one index, one objective and 20 coordinates. It has 21 single spaces and no trailing space. With a three-digit index and 24 bytes per numeric field, each row is at most `3 + 21*24 + 21 = 528` bytes. The joined table has `n-1` internal LF characters; the template already accounts for the LF immediately outside the placeholder.

- 200 rows: `200*528 + 199 = 105,799`; add 2,940 = **108,739**.
- 190 rows: `190*528 + 189 = 100,509`; add 2,940 = **103,449**.

The runner correction appends exactly a 29-byte prefix (including an added LF), one fixed reason, and a 51-byte suffix. Reasons are `invalid_json` (12), `invalid_envelope` (16), or `no_valid_vectors` (16) bytes. The longest correction therefore adds **96 bytes**. The template already ends with LF, so the additional LF really is an extra byte and is included here. No prior response body is included.

Prompt hashes, recomputed from the checked text:

- System: `5165cfc31f62b008e0cb7f88c24ea72b286da75f43cc5d6e4e3f36e7d6397f7e`.
- User template: `80aa634b5511134e9a741614f60d341422f38143e05136da3f3f2e159bf44ba1`.

## Fabricated-only validation and limits

A deterministic local fixture sweep examined 403,582 finite float entries: signs of seeded random binary64 bit patterns, zero/signed zero, largest finite/minimum normal/minimum subnormal, decimal-power neighbors across the finite range, and fixed/scientific boundary examples. Maximum observed repr length was 24. This finite sweep supports the derivation but does not prove it by exhaustive enumeration.

A valid 190-row synthetic history used the 24-byte negative minimum-normal coordinate in every coordinate position and an arbitrary minimum-normal objective. `render_user(history, 19)` succeeded and the combined system/user text contained **103,146** ASCII bytes, below the conservative 103,449 bound. Those values were fabricated; no Hamiltonian, simulator output, objective instance or optimizer was evaluated. The row indexes remained unique and the coordinate pairs satisfied the mapped-domain validation.

The renderer validates `batch` in 1..19 and unique indexes in 1..10*batch; it cannot render 200 rows. The 200-row result is a conservative prospective protocol boundary derived from the same table grammar, not a claim that a 200-row call was accepted by the current renderer.

Do not convert bytes to tokens by dividing by four or simply asserting one token per byte. A provider may add role delimiters, hidden instructions, configuration text and other formatting; the actual model/tokenizer contract remains unverified. This result is useful for an offline size guard and for constructing E9/token-counting fixtures. It does not satisfy G-MODEL or G-COST, and any new wrapper, prompt amendment, extra field or correction text requires recomputation.
