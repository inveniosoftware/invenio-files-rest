# -*- coding: utf-8 -*-
#
# Copyright 2007 Pallets
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1.  Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#
# 2.  Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# 3.  Neither the name of the copyright holder nor the names of its
#     contributors may be used to endorse or promote products derived from
#     this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""WSGI-related utilities for Files REST API."""


class RangeFileWrapper:
    """Wrap a file-like object with a range constraint.

    NOTE: This is a copy of _RangeFileWrapper from werkzeug.wsgi made public.
    If that class should ever be made public, we should use it instead.

    This class can be used to convert an iterable object into
    an iterable that will only yield a piece of the underlying content.
    It yields blocks until the underlying stream range is fully read.

    :param iterable: an iterable object with a __next__ method.
    :param start_byte: byte from which read will start.
    :param byte_range: how many bytes to read.
    """

    def __init__(self, iterable, start_byte=0, byte_range=None):
        """Initialize the wrapper with the given iterable and range parameters.

        :param iterable: The iterable to wrap.
        :param start_byte: The byte offset to start reading from.
        :param byte_range: The number of bytes to read.
        """
        self.iterable = iter(iterable)
        self.byte_range = byte_range
        self.start_byte = start_byte
        self.end_byte = None

        if byte_range is not None:
            self.end_byte = start_byte + byte_range

        self.read_length = 0
        self.seekable = hasattr(iterable, "seekable") and iterable.seekable()
        self.end_reached = False

    def __iter__(self):
        """Return self as iterator.

        :returns: Self as iterator.
        """
        return self

    def _next_chunk(self):
        """Get the next chunk from the iterable.

        :returns: The next chunk of data.
        :raises StopIteration: When the iterable is exhausted.
        """
        try:
            chunk = next(self.iterable)
            self.read_length += len(chunk)
            return chunk
        except StopIteration:
            self.end_reached = True
            raise

    def _first_iteration(self):
        """Handle the first iteration to position at the start byte.

        This method handles both seekable and non-seekable iterables.
        For seekable iterables, it uses seek() to position at the start byte.
        For non-seekable iterables, it reads and discards data until the start byte.

        :returns: A tuple of (chunk, contextual_read_length) where chunk is the
                 first chunk of data after positioning and contextual_read_length
                 is the effective read position.
        """
        chunk = None
        if self.seekable:
            self.iterable.seek(self.start_byte)
            self.read_length = self.iterable.tell()
            contextual_read_length = self.read_length
        else:
            while self.read_length <= self.start_byte:
                chunk = self._next_chunk()
            if chunk is not None:
                chunk = chunk[self.start_byte - self.read_length + len(chunk) :]
            contextual_read_length = self.start_byte
        return chunk, contextual_read_length

    def _next(self):
        """Get the next chunk of data respecting the byte range constraints.

        This method handles the logic for getting the next chunk of data,
        including special handling for the first iteration and enforcing
        the end byte limit.

        :returns: The next chunk of data within the specified byte range.
        :raises StopIteration: When the end of the range or iterable is reached.
        """
        if self.end_reached:
            raise StopIteration()
        chunk = None
        contextual_read_length = self.read_length
        if self.read_length == 0:
            chunk, contextual_read_length = self._first_iteration()
        if chunk is None:
            chunk = self._next_chunk()
        if self.end_byte is not None and self.read_length >= self.end_byte:
            self.end_reached = True
            return chunk[: self.end_byte - contextual_read_length]
        return chunk

    def __next__(self):
        """Get the next chunk of data from the iterator.

        This method is part of the iterator protocol and is called
        when the iterator is used in a for loop or with the next() function.

        :returns: The next chunk of data.
        :raises StopIteration: When there is no more data to read.
        """
        chunk = self._next()
        if chunk:
            return chunk
        self.end_reached = True
        raise StopIteration()

    def close(self):
        """Close the underlying iterable if it has a close method.

        This method should be called when the wrapper is no longer needed
        to ensure that any resources held by the underlying iterable are released.
        """
        if hasattr(self.iterable, "close"):
            self.iterable.close()
