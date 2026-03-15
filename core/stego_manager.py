"""
Stego Manager — Hides and extracts encrypted data in images using LSB steganography.
Uses a length-prefix header instead of a fixed delimiter for security.
"""
import cv2
import numpy as np
import struct
import zlib


# 4-byte big-endian length header
HEADER_SIZE = 4  # bytes → supports payloads up to ~4 GB


class StegoManager:
    """LSB Steganography engine with compression and length-prefix framing."""

    def _to_bits(self, data):
        """Convert bytes to a bit string."""
        return "".join(format(byte, "08b") for byte in data)

    def _capacity(self, image):
        """Calculate how many bytes can be hidden in this image."""
        return (image.shape[0] * image.shape[1] * 3) // 8

    def hide_data(self, image_path, output_path, secret_data):
        """
        Hide bytes inside an image using LSB steganography.

        The data is compressed, then framed as:
            [4-byte length header] + [compressed payload]

        Args:
            image_path: Path to the cover image.
            output_path: Where to save the stego image (must be .png).
            secret_data: bytes to hide.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Compress
        compressed = zlib.compress(secret_data, level=9)

        # Frame: 4-byte big-endian length + payload
        length_header = struct.pack(">I", len(compressed))
        framed_data = length_header + compressed

        # Capacity check
        capacity = self._capacity(image)
        if len(framed_data) > capacity:
            raise ValueError(
                f"Insufficient space! Need {len(framed_data):,} bytes, "
                f"image can hold {capacity:,} bytes."
            )

        # Convert to bit string
        bits = self._to_bits(framed_data)
        bit_len = len(bits)
        bit_idx = 0

        # Embed bits into LSB of each color channel
        for row in image:
            for pixel in row:
                for c in range(3):
                    if bit_idx < bit_len:
                        # Clear LSB and set it to our bit
                        pixel[c] = (int(pixel[c]) & 0xFE) | int(bits[bit_idx])
                        bit_idx += 1
                    else:
                        break
                if bit_idx >= bit_len:
                    break
            if bit_idx >= bit_len:
                break

        # Save losslessly as PNG
        cv2.imwrite(output_path, image)

    def extract_data(self, image_path):
        """
        Extract hidden data from a stego image.

        Reads the 4-byte length header first, then extracts only the
        required number of bits (much faster than scanning the entire image).

        Args:
            image_path: Path to the stego image.

        Returns:
            bytes: The original hidden data.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # First, extract the 4-byte length header (= 32 bits)
        header_bits = self._extract_bits(image, HEADER_SIZE * 8)
        header_bytes = self._bits_to_bytes(header_bits)
        payload_length = struct.unpack(">I", header_bytes)[0]

        # Sanity check
        max_payload = self._capacity(image) - HEADER_SIZE
        if payload_length > max_payload or payload_length == 0:
            raise ValueError("No hidden data found or image is corrupted.")

        # Now extract exactly the payload (skip header bits)
        total_bits_needed = (HEADER_SIZE + payload_length) * 8
        all_bits = self._extract_bits(image, total_bits_needed)

        # Skip the header bits, take only payload
        payload_bits = all_bits[HEADER_SIZE * 8:]
        compressed_data = self._bits_to_bytes(payload_bits)

        # Decompress
        try:
            return zlib.decompress(compressed_data)
        except zlib.error:
            raise ValueError("Data corruption detected — decompression failed.")

    def _extract_bits(self, image, num_bits):
        """Extract `num_bits` from the LSBs of the image pixels."""
        bits = []
        count = 0

        for row in image:
            for pixel in row:
                for c in range(3):
                    if count < num_bits:
                        bits.append(str(int(pixel[c]) & 1))
                        count += 1
                    else:
                        return "".join(bits)
            if count >= num_bits:
                break

        return "".join(bits)

    def _bits_to_bytes(self, bit_string):
        """Convert a bit string to bytes."""
        byte_list = []
        for i in range(0, len(bit_string), 8):
            byte_list.append(int(bit_string[i:i + 8], 2))
        return bytes(byte_list)